// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The offsets editor (the Python screens/shared/offsets_editor.py and components/signed_gauge.py): an arpeggiator's
//! offsets in a row, each step's offset a bar rising or falling from the zero line, a blank step silent.

use crate::app::App;
use crate::keybindings::{Binding, KeyClass, OffsetsEditor as Keys};
use crate::keys::KeyItem;
use crate::screens::one_row_editor::{Edge, GridLine, OneRow};
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Item;
use llamatron_strings::{labels, marks, messages, named};

const CELL_WIDTH: usize = 6;
const MOST: i64 = 24;
const MOST_STEPS: usize = 16;
const LINES_AROUND_GAUGE: usize = 7;
const MAX_GAUGE_LEVELS: usize = 7;
const SECTION: &str = "arps";

pub struct OffsetsEditor {
    pub name: String,
}

/// What an offset that moves its note nowhere is, as a new or a played-again step holds.
const NO_OFFSET: i64 = 0;

impl OffsetsEditor {
    /// Store the arp's offsets, or take them out of the file with None.
    fn store(&self, app: &mut App, offsets: Option<Vec<Option<i64>>>) {
        let name = self.name.clone();
        let value = offsets.map(|offsets| {
            Data::List(
                offsets
                    .iter()
                    .map(|offset| offset.map_or(Data::Null, |whole| Data::Whole(whole as i128)))
                    .collect(),
            )
        });
        app.document.change_set(|setlist| {
            if let Some(Item::Generator(settings)) = setlist.get_item_mut(SECTION, &name) {
                settings.set_written("offsets", value);
            }
        });
    }

    fn offsets(&self, app: &App) -> Vec<Option<i64>> {
        match app.document.get_setlist().get_item(SECTION, &self.name) {
            Some(Item::Generator(settings)) => settings.get_written("offsets").and_then(Data::as_list).map_or(Vec::new(), |offsets| {
                offsets.iter().map(|offset| offset.as_whole().map(|whole| whole as i64)).collect()
            }),
            _ => Vec::new(),
        }
    }
}

/// A step's offset as the gauge's number row shows it: signed, marked where it passes the gauge's top or bottom.
fn value_text(value: Option<i64>, levels: i64, cursor: bool) -> String {
    let text = match value {
        None => String::new(),
        Some(value) => {
            let mark = if value > levels {
                marks::MSG_OVER_THE_TOP_MARK
            } else if value < -levels {
                marks::MSG_UNDER_THE_BOTTOM_MARK
            } else {
                ""
            };
            named(
                if value > 0 { marks::MSG_POSITIVE_VALUE } else { marks::MSG_OTHER_VALUE },
                &[("value", value.into()), ("mark", mark.into())],
            )
        }
    };
    if cursor {
        named(marks::MSG_CURSOR_VALUE_MARKS, &[("text", text.as_str().into())])
    } else {
        text
    }
}

fn gauge_cell(value: Option<i64>, level: i64) -> String {
    match value {
        Some(value) if (level > 0 && value >= level) || (level < 0 && value <= level) => marks::MSG_GAUGE_BAR.to_string(),
        _ => String::new(),
    }
}

impl OneRow for OffsetsEditor {
    fn name(&self) -> &'static str {
        "OffsetsEditor"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![
            labels::Crumb::GENERATORS.to_string(),
            named(labels::MSG_ITEM_CRUMB, &[("name", self.name.as_str().into())]),
            labels::Crumb::OFFSETS.to_string(),
        ]
    }

    fn caption(&self, _app: &App) -> String {
        let what = llamatron_strings::plugin_texts::arp::MSG_CAPTION_WORD.to_uppercase();
        named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", self.name.as_str().into())],
        )
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::GENERATORS)
    }

    fn cell_width(&self) -> usize {
        CELL_WIDTH
    }

    fn most(&self) -> i64 {
        MOST
    }

    fn most_steps(&self) -> usize {
        MOST_STEPS
    }

    fn insert(&self) -> &'static Binding {
        &Keys::INSERT_STEP
    }

    fn remove(&self) -> &'static Binding {
        &Keys::REMOVE_STEP
    }

    fn values(&self, app: &App) -> Vec<Option<i64>> {
        self.offsets(app)
    }

    fn set_value(&mut self, app: &mut App, step: usize, value: Option<i64>) {
        let mut offsets = self.offsets(app);
        if step < offsets.len() {
            offsets[step] = value;
            self.store(app, Some(offsets));
        }
    }

    /// A new step plays its note unmoved.
    fn add_step(&mut self, app: &mut App, step: usize) {
        let mut offsets = self.offsets(app);
        offsets.insert(step.min(offsets.len()), Some(NO_OFFSET));
        self.store(app, Some(offsets));
    }

    /// The last step taken out leaves no offsets at all.
    fn remove_step_here(&mut self, app: &mut App, step: usize) {
        let mut offsets = self.offsets(app);
        if step < offsets.len() {
            offsets.remove(step);
        }
        let kept = (!offsets.is_empty()).then_some(offsets);
        self.store(app, kept);
    }

    /// Space and ENTER make a step silent, or play its note unmoved again.
    fn press_more(&mut self, app: &mut App, item: &KeyItem, _key: &str, step: usize) {
        if item.is(&Keys::SILENT) || item.is(&Keys::PLAY) {
            let here = self.offsets(app).get(step).copied().flatten();
            let value = if here.is_none() { Some(NO_OFFSET) } else { None };
            self.set_value(app, step, value);
        }
    }

    fn more_keys_at(&self, app: &App, step: usize) -> Vec<KeyItem> {
        let here = self.offsets(app).get(step).copied().flatten();
        vec![KeyItem::of(&Keys::CLASS, if here.is_some() { &Keys::SILENT } else { &Keys::PLAY })]
    }

    fn lines(&self, app: &App, heading: &dyn Fn(String, bool, bool) -> GridLine, window: (usize, usize, usize), step: usize) -> Vec<GridLine> {
        let (first, last, height) = window;
        let offsets = self.offsets(app);
        let levels = (height.saturating_sub(LINES_AROUND_GAUGE) / 2).clamp(1, MAX_GAUGE_LEVELS) as i64;
        let count = last - first;
        let step_text = |place: usize| {
            if place == step {
                named(marks::MSG_CURSOR_STEP_MARKS, &[("text", (place + 1).to_string().as_str().into())])
            } else {
                (place + 1).to_string()
            }
        };
        let mut lines = vec![
            heading(messages::MSG_OFFSETS_NOTE.to_string(), true, false),
            GridLine::Drawn(crate::text::Text::default()),
            GridLine::Rule { edge: Edge::Top, count },
        ];
        lines.push(GridLine::Row {
            label: labels::MSG_STEP_ROW_LABEL.to_string(),
            cells: (first..last).map(|place| (place, step_text(place))).collect(),
            selected: Some(step),
            bold: true,
        });
        for level in (1..=levels).rev() {
            lines.push(GridLine::Row {
                label: String::new(),
                cells: (first..last).map(|place| (place, gauge_cell(offsets[place], level))).collect(),
                selected: None,
                bold: false,
            });
        }
        lines.push(GridLine::Rule { edge: Edge::Across, count });
        for level in (-levels..=-1).rev() {
            lines.push(GridLine::Row {
                label: String::new(),
                cells: (first..last).map(|place| (place, gauge_cell(offsets[place], level))).collect(),
                selected: None,
                bold: false,
            });
        }
        lines.push(GridLine::Row {
            label: labels::MSG_OFFSET_ROW_LABEL.to_string(),
            cells: (first..last).map(|place| (place, value_text(offsets[place], levels, place == step))).collect(),
            selected: Some(step),
            bold: false,
        });
        lines.push(GridLine::Rule { edge: Edge::Bottom, count });
        lines
    }
}
