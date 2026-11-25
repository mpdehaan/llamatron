// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A Guitarify's bar (the Python screens/shared/guitar_bar_editor.py): a stroke a cell, each accented or not, and how long
//! a cell lasts.

use crate::app::App;
use crate::forms::nodes::stepped;
use crate::generated::tables::{DEFAULT_BAR, READY_BARS};
use crate::keybindings::{Binding, GuitarBarEditor as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::screens::generators::plugin_editor::caption_word;
use crate::screens::one_row_editor::{Edge, GridLine, OneRow};
use crate::settings::named_in;
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::STROKES;
use llamatron_strings::{labels, marks, messages, named};

const KIND: &str = "guitarify";
const SECTION: &str = "guitarifies";
const CELL_WIDTH: usize = 3;
const MOST_CELLS: usize = 32;
/// The cell lengths S steps through, in order.
const CELL_LENGTHS: [&str; 5] = ["1/4", "1/8", "1/16", "1/12", "1/32"];
const NOTHING: &str = "nothing";

/// A bar of strokes: a stroke a cell, whether each is accented, and how long a cell lasts.
pub struct GuitarBar {
    pub strokes: Vec<String>,
    pub accents: Vec<bool>,
    pub cell: String,
}

fn text_of(value: &Data) -> String {
    value.as_str().map_or_else(|| format!("{value:?}"), str::to_string)
}

impl GuitarBar {
    /// A Guitarify's bar as its settings hold it, the default ready-made bar where they leave it out.
    pub fn of(written: &dyn Fn(&str) -> Option<Data>) -> GuitarBar {
        let (_, default_cell, default_strokes, default_accents) = READY_BARS
            .iter()
            .find(|(name, ..)| *name == DEFAULT_BAR)
            .expect("the default bar is ready-made");
        let bar = written("bar");
        let strokes: Vec<String> = bar
            .as_ref()
            .and_then(Data::as_list)
            .map(|strokes| strokes.iter().map(text_of).collect())
            .unwrap_or_else(|| default_strokes.iter().map(|stroke| stroke.to_string()).collect());
        let accents_written = written("accents");
        let accents = if bar.is_none() && accents_written.is_none() {
            default_accents.to_vec()
        } else {
            let listed: Vec<bool> = accents_written
                .as_ref()
                .and_then(Data::as_list)
                .map_or(Vec::new(), |items| items.iter().map(|item| matches!(item, Data::Bool(true))).collect());
            (0..strokes.len()).map(|place| listed.get(place).copied().unwrap_or(false)).collect()
        };
        let cell = written("cell").map_or(default_cell.to_string(), |cell| text_of(&cell));
        GuitarBar { strokes, accents, cell }
    }
}

pub struct GuitarBarEditor {
    pub name: String,
}

impl GuitarBarEditor {
    fn bar(&self, app: &App) -> GuitarBar {
        let setlist = app.document.get_setlist();
        let settings = match setlist.get_item(SECTION, &self.name) {
            Some(Item::Generator(settings)) => Some(settings),
            _ => None,
        };
        GuitarBar::of(&|name| {
            settings
                .and_then(|settings| settings.get_written(name))
                .filter(|value| !value.is_null())
                .cloned()
        })
    }

    fn store(&self, app: &mut App, bar: GuitarBar) {
        let name = self.name.clone();
        app.document.change_set(|setlist| {
            if let Some(Item::Generator(settings)) = setlist.get_item_mut(SECTION, &name) {
                settings.set_written("bar", Some(Data::List(bar.strokes.into_iter().map(Data::Text).collect())));
                settings.set_written("accents", Some(Data::List(bar.accents.into_iter().map(Data::Bool).collect())));
                settings.set_written("cell", Some(Data::Text(bar.cell)));
            }
        });
    }

    fn bind(binding: &'static Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }
}

impl OneRow for GuitarBarEditor {
    fn name(&self) -> &'static str {
        "GuitarBarEditor"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![
            labels::Crumb::GENERATORS.to_string(),
            named(labels::MSG_ITEM_CRUMB, &[("name", self.name.as_str().into())]),
            labels::Crumb::STROKES.to_string(),
        ]
    }

    fn caption(&self, _app: &App) -> String {
        let what = caption_word(KIND).to_uppercase();
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
        1
    }

    fn most_steps(&self) -> usize {
        MOST_CELLS
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

    fn steps_values(&self) -> bool {
        false
    }

    fn move_binding(&self) -> &'static Binding {
        &Keys::MOVE
    }

    fn values(&self, app: &App) -> Vec<Option<i64>> {
        vec![Some(0); self.bar(app).strokes.len()]
    }

    fn more_keys(&self, _app: &App) -> Vec<KeyItem> {
        [&Keys::LESS, &Keys::MORE, &Keys::ACCENT, &Keys::CELL_LENGTH, &Keys::READY_BARS]
            .into_iter()
            .map(Self::bind)
            .collect()
    }

    fn press_more(&mut self, app: &mut App, item: &KeyItem, _key: &str, step: usize) {
        let mut bar = self.bar(app);
        let strokes: Vec<String> = STROKES.iter().map(|stroke| stroke.to_string()).collect();
        if item.is(&Keys::LESS) || item.is(&Keys::MORE) {
            let offset = if item.is(&Keys::LESS) { -1 } else { 1 };
            bar.strokes[step] = stepped(&strokes, &bar.strokes[step], offset);
        } else if item.is(&Keys::ACCENT) {
            bar.accents[step] = !bar.accents[step];
        } else if item.is(&Keys::INSERT_CELL) {
            bar.strokes.insert(step, NOTHING.to_string());
            bar.accents.insert(step, false);
        } else if item.is(&Keys::REMOVE_CELL) {
            bar.strokes.remove(step);
            bar.accents.remove(step);
        } else if item.is(&Keys::CELL_LENGTH) {
            bar.cell = match CELL_LENGTHS.iter().position(|length| *length == bar.cell) {
                Some(place) => CELL_LENGTHS[(place + 1) % CELL_LENGTHS.len()].to_string(),
                None => CELL_LENGTHS[0].to_string(),
            };
        } else {
            // The ready-made bars are chosen in a dialog, not ported yet.
            return;
        }
        self.store(app, bar);
    }

    fn lines(&self, app: &App, heading: &dyn Fn(String, bool, bool) -> GridLine, window: (usize, usize, usize), step: usize) -> Vec<GridLine> {
        let (first, last, _) = window;
        let bar = self.bar(app);
        let count = last - first;
        let note = if bar.accents[step] {
            messages::MSG_GUITAR_CELL_ACCENTED_NOTE
        } else {
            messages::MSG_GUITAR_CELL_NOTE
        };
        let stroke = named_in(labels::MSG_GUITAR_STROKE_NAMES, &bar.strokes[step]);
        vec![
            heading(named(messages::MSG_GUITAR_BAR_NOTE, &[("cell", bar.cell.as_str().into())]), true, false),
            GridLine::Drawn(Text::plain(&named(note, &[("number", (step + 1).into()), ("stroke", stroke.as_str().into())]))),
            GridLine::Drawn(Text::default()),
            GridLine::Rule { edge: Edge::Top, count },
            GridLine::Row {
                label: labels::MSG_CELL_ROW_LABEL.to_string(),
                cells: (first..last).map(|place| (place, (place + 1).to_string())).collect(),
                selected: None,
                bold: true,
            },
            GridLine::Rule { edge: Edge::Across, count },
            GridLine::Row {
                label: labels::MSG_STROKE_ROW_LABEL.to_string(),
                cells: (first..last)
                    .map(|place| (place, named_in(marks::MSG_STROKE_MARKS, &bar.strokes[place])))
                    .collect(),
                selected: Some(step),
                bold: false,
            },
            GridLine::Row {
                label: labels::MSG_ACCENT_ROW_LABEL.to_string(),
                cells: (first..last)
                    .map(|place| (place, if bar.accents[place] { marks::MSG_TOGGLE_ON } else { marks::MSG_TOGGLE_OFF }.to_string()))
                    .collect(),
                selected: None,
                bold: false,
            },
            GridLine::Rule { edge: Edge::Bottom, count },
        ]
    }
}
