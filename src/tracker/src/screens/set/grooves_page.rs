// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Grooves page (the Python screens/set/grooves_page.py and pages/groove_list.py): the factory grooves every set has,
//! then the set's own, each with its cells, its cell length and its uses; a factory groove can only be looked at and copied.

use crate::app::App;
use crate::drawing::Align;
use crate::keybindings::{GroovesPage as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::screens::list_page::{named_item_keys, ListColumn, Listing, NamedWords, Row};
use crate::screens::one_row_editor::OneRowEditor;
use crate::screens::set::groove_editor::{groove_of, GrooveEditor};
use crate::themes::{self, Colour};
use crate::uses::uses_of;
use llamatron_engine::groove::FACTORY_GROOVES;
use llamatron_model::file::data::Data;
use llamatron_model::objects::named::Groove;
use llamatron_model::objects::naming::new_name;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::{GrooveSetting, Section};
use llamatron_strings::{labels, marks, names};

/// How many cells a new groove has: one bar of straight 16ths.
const GROOVE_CELLS: usize = 16;

const COLUMNS: [ListColumn; 5] = [
    ListColumn {
        heading: labels::Column::SELECT_GROOVE,
        width: None,
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::FROM,
        width: Some(9),
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::CELLS,
        width: Some(40),
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::CELL,
        width: Some(5),
        align: Align::Right,
    },
    ListColumn {
        heading: labels::Column::USED,
        width: Some(4),
        align: Align::Right,
    },
];

/// Whether a groove is one of the factory grooves.
pub fn is_factory(name: &str) -> bool {
    FACTORY_GROOVES.iter().any(|(found, _, _)| *found == name)
}

/// Every groove a song can choose: the factory ones, then the set's own.
pub fn groove_names(app: &App) -> Vec<String> {
    let mut names: Vec<String> = FACTORY_GROOVES.iter().map(|(name, _, _)| name.to_string()).collect();
    names.extend(app.document.get_setlist().items(Section::GROOVES).iter().map(|(name, _)| name.clone()));
    names
}

/// Numbers with a space between them and a dash for each that isn't set, like 74 - - 1.
pub fn numbers_text(numbers: &[Option<i64>]) -> String {
    numbers
        .iter()
        .map(|number| number.map_or(marks::MSG_NO_NUMBER_MARK.to_string(), |number| number.to_string()))
        .collect::<Vec<_>>()
        .join(" ")
}

pub struct GroovesPage;

impl Listing for GroovesPage {
    fn name(&self) -> &'static str {
        "GroovesPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::GROOVES.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::GROOVES)
    }

    fn columns(&self) -> &[ListColumn] {
        &COLUMNS
    }

    fn rows(&self, app: &App) -> Vec<Row> {
        let setlist = app.document.get_setlist();
        let mut rows = Vec::new();
        for name in groove_names(app) {
            let (cells, length) = groove_of(app, &name);
            let source = if is_factory(&name) {
                marks::MSG_FACTORY_GROOVE_SHOWN
            } else {
                marks::MSG_OWN_GROOVE_SHOWN
            };
            let uses = uses_of(setlist, Section::GROOVES, &name).len();
            rows.push((name.clone(), vec![name, source.to_string(), numbers_text(&cells), length, uses.to_string()]));
        }
        rows
    }

    fn item_keys(&self, _app: &App) -> Vec<KeyItem> {
        named_item_keys(&Keys::CLASS, &Keys::EDIT)
    }

    fn row_keys(&self, _app: &App, row: &str) -> Option<Vec<KeyItem>> {
        is_factory(row).then(|| vec![KeyItem::of(&Keys::CLASS, &Keys::VIEW), KeyItem::of(&Keys::CLASS, &Keys::COPY)])
    }

    fn named(&self) -> Option<NamedWords> {
        Some(NamedWords {
            section: "grooves",
            rename_prompt: llamatron_strings::messages::MSG_RENAME_GROOVE_PROMPT,
            what: llamatron_strings::legends::MSG_GROOVE_WHAT,
        })
    }

    fn press_row(&mut self, app: &mut App, item: &KeyItem, _key: &str, row: Option<&str>) -> Option<String> {
        if item.is(&Keys::ADD) || item.is(&Keys::ADD_HERE) {
            let name = new_name(names::MSG_NEW_GROOVE_WORD, &groove_names(app));
            let cells = Data::List(vec![Data::Whole(0); GROOVE_CELLS]);
            let groove = Groove::from_data(&Data::Map(vec![(Data::text(GrooveSetting::CELLS), cells)])).expect("a straight groove reads");
            app.document
                .change_set(|setlist| setlist.add_item(Section::GROOVES, &name, Item::Groove(groove)));
            app.show_page(Box::new(OneRowEditor::new(GrooveEditor { name: name.clone() })));
            return Some(name);
        }
        if let (true, Some(name)) = (item.is(&Keys::EDIT) || item.is(&Keys::VIEW), row) {
            app.show_page(Box::new(OneRowEditor::new(GrooveEditor { name: name.to_string() })));
        }
        None
    }
}
