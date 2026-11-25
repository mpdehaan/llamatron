// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A chain's page (the Python screens/generators/chain_editor.py and pages/chain.py): its steps in the order they run, each a
//! generator's kind and name, a generator that comes again counted.

use crate::app::App;
use crate::drawing::Align;
use crate::keybindings::{ChainEditor as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::screens::field_page::FieldPage;
use crate::screens::generators::generators_page::label_of;
use crate::screens::generators::statements_page::{GeneratorStatementsPage, Holder};
use crate::screens::list_page::{ListColumn, Listing, Row};
use crate::settings::named_in;
use crate::themes::{self, Colour};
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::Section;
use llamatron_strings::{labels, marks, named};

const COLUMNS: [ListColumn; 1] = [ListColumn {
    heading: labels::Column::SELECT_ANY_GENERATOR,
    width: None,
    align: Align::Left,
}];
/// The count a generator that comes again in a chain is first shown with.
const FIRST_REPEAT: usize = 2;

pub struct ChainEditor {
    pub name: String,
}

/// A chain's steps as its list shows them, each its kind's name before its own, counted where it comes again.
pub fn steps_shown(steps: &[(String, String)]) -> Vec<String> {
    let mut seen: Vec<(&(String, String), usize)> = Vec::new();
    let mut shown = Vec::new();
    for step in steps {
        let count = match seen.iter_mut().find(|(found, _)| *found == step) {
            Some((_, count)) => {
                *count += 1;
                *count
            }
            None => {
                seen.push((step, 1));
                1
            }
        };
        let (kind, name) = step;
        let label = label_of(kind);
        if count >= FIRST_REPEAT {
            shown.push(named(
                marks::MSG_CHAIN_STEP_AGAIN,
                &[("name", name.as_str().into()), ("number", count.into()), ("kind", label.into())],
            ));
        } else {
            shown.push(named(marks::MSG_CHAIN_STEP_SHOWN, &[("name", name.as_str().into()), ("kind", label.into())]));
        }
    }
    shown
}

impl ChainEditor {
    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }
}

impl Listing for ChainEditor {
    fn name(&self) -> &'static str {
        "ChainEditor"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![
            labels::Crumb::GENERATORS.to_string(),
            named(labels::MSG_ITEM_CRUMB, &[("name", self.name.as_str().into())]),
        ]
    }

    fn caption(&self, _app: &App) -> Option<String> {
        let what = named_in(labels::MSG_CAPTION_WORDS, Section::CHAINS).to_uppercase();
        Some(named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", self.name.as_str().into())],
        ))
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::GENERATORS)
    }

    fn columns(&self) -> &[ListColumn] {
        &COLUMNS
    }

    fn rows(&self, app: &App) -> Vec<Row> {
        let Some(Item::Chain(chain)) = app.document.get_setlist().get_item(Section::CHAINS, &self.name) else {
            return Vec::new();
        };
        steps_shown(chain.get_steps())
            .into_iter()
            .enumerate()
            .map(|(place, text)| (place.to_string(), vec![text]))
            .collect()
    }

    fn item_keys(&self, _app: &App) -> Vec<KeyItem> {
        [&Keys::CHANGE, &Keys::COPY, &Keys::REMOVE, &Keys::MOVE].into_iter().map(Self::bind).collect()
    }

    fn always_keys(&self, _app: &App) -> Vec<KeyItem> {
        vec![Self::bind(&Keys::RENAME), Self::bind(&Keys::WHEN)]
    }

    /// Adding, changing a step and renaming ask in dialogs, not ported yet.
    fn press_row(&mut self, app: &mut App, item: &KeyItem, _key: &str, _row: Option<&str>) -> Option<String> {
        if item.is(&Keys::WHEN) {
            let page = GeneratorStatementsPage {
                holder: Holder::Chain(self.name.clone()),
            };
            app.show_page(Box::new(FieldPage::new(page)));
        }
        None
    }
}
