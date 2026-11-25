// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A generator's row of steps, each on or off (the Python screens/shared/step_row_editor.py), such as the steps a Timing
//! rushes.

use crate::app::App;
use crate::keybindings::{Binding, KeyClass, StepRowEditor as Keys};
use crate::keys::KeyItem;
use crate::screens::generators::plugin_editor::caption_word;
use crate::screens::one_row_editor::{Edge, GridLine, OneRow};
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::limits::{MAX_STEP_ROW, MIN_STEP_ROW};
use llamatron_strings::{labels, marks, named};

const CELL_WIDTH: usize = 5;
/// The row a generator holds where its file leaves it out.
const UNLIT_STEPS: usize = 4;

pub struct StepRowEditor {
    /// The generator: its kind, its section and its name.
    pub kind: &'static str,
    pub section: &'static str,
    pub name: String,
    /// The setting that holds the row, the row's name and what the row does.
    pub setting: &'static str,
    pub row_name: &'static str,
    pub note: &'static str,
}

impl StepRowEditor {
    fn steps(&self, app: &App) -> Vec<bool> {
        let written = match app.document.get_setlist().get_item(self.section, &self.name) {
            Some(Item::Generator(settings)) => settings.get_written(self.setting).and_then(Data::as_list).map(<[Data]>::to_vec),
            _ => None,
        };
        match written {
            Some(steps) => steps.iter().map(|step| matches!(step, Data::Bool(true))).collect(),
            None => vec![false; UNLIT_STEPS],
        }
    }

    fn store(&self, app: &mut App, steps: Vec<bool>) {
        let (section, name, setting) = (self.section, self.name.clone(), self.setting);
        app.document.change_set(|setlist| {
            if let Some(Item::Generator(settings)) = setlist.get_item_mut(section, &name) {
                settings.set_written(setting, Some(Data::List(steps.into_iter().map(Data::Bool).collect())));
            }
        });
    }
}

impl OneRow for StepRowEditor {
    fn name(&self) -> &'static str {
        "StepRowEditor"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![
            labels::Crumb::GENERATORS.to_string(),
            named(labels::MSG_ITEM_CRUMB, &[("name", self.name.as_str().into())]),
            labels::Crumb::STEPS.to_string(),
        ]
    }

    fn caption(&self, _app: &App) -> String {
        let what = caption_word(self.kind).to_uppercase();
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
        MAX_STEP_ROW as usize
    }

    fn fewest_steps(&self) -> usize {
        MIN_STEP_ROW as usize
    }

    fn insert(&self) -> &'static Binding {
        &Keys::INSERT_STEP
    }

    fn remove(&self) -> &'static Binding {
        &Keys::REMOVE_STEP
    }

    fn steps_values(&self) -> bool {
        false
    }

    fn move_binding(&self) -> &'static Binding {
        &Keys::MOVE
    }

    fn values(&self, app: &App) -> Vec<Option<i64>> {
        self.steps(app).into_iter().map(|on| Some(on as i64)).collect()
    }

    fn more_keys_at(&self, _app: &App, _step: usize) -> Vec<KeyItem> {
        vec![KeyItem::of(&Keys::CLASS, &Keys::TOGGLE)]
    }

    fn press_more(&mut self, app: &mut App, item: &KeyItem, _key: &str, step: usize) {
        let mut steps = self.steps(app);
        if item.is(&Keys::TOGGLE) {
            steps[step] = !steps[step];
        } else if item.is(&Keys::INSERT_STEP) {
            steps.insert(step, false);
        } else if item.is(&Keys::REMOVE_STEP) {
            steps.remove(step);
        } else {
            return;
        }
        self.store(app, steps);
    }

    fn lines(&self, app: &App, heading: &dyn Fn(String, bool, bool) -> GridLine, window: (usize, usize, usize), step: usize) -> Vec<GridLine> {
        let (first, last, _) = window;
        let steps = self.steps(app);
        let count = last - first;
        vec![
            heading(self.note.to_string(), true, false),
            GridLine::Drawn(crate::text::Text::default()),
            GridLine::Rule { edge: Edge::Top, count },
            GridLine::Row {
                label: labels::MSG_STEP_NUMBER_ROW_LABEL.to_string(),
                cells: (first..last).map(|place| (place, (place + 1).to_string())).collect(),
                selected: Some(step),
                bold: true,
            },
            GridLine::Rule { edge: Edge::Across, count },
            GridLine::Row {
                label: self.row_name.to_string(),
                cells: (first..last)
                    .map(|place| (place, if steps[place] { marks::MSG_TOGGLE_ON } else { marks::MSG_TOGGLE_OFF }.to_string()))
                    .collect(),
                selected: Some(step),
                bold: false,
            },
            GridLine::Rule { edge: Edge::Bottom, count },
        ]
    }
}
