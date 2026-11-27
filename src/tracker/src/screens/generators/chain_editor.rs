// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A chain's page (the Python screens/generators/chain_editor.py and pages/chain.py): its steps in the order they run, each a
//! generator's kind and name, a generator that comes again counted.

use crate::app::App;
use crate::drawing::Align;
use crate::keybindings::{ChainEditor as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::screens::dialogs::{Answer, ChoiceDialog};
use crate::screens::generators::generators_page::label_of;
use crate::screens::generators::generators_page::{editor_of, listed_kinds, new_generator, GeneratorChosen};
use crate::screens::list_page::{ListColumn, Listing, Row};
use crate::settings::named_in;
use crate::themes::{self, Colour};
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::Section;
use llamatron_model::schema::generated::file_format::CHAIN_KIND;
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_strings::{labels, marks, messages, named};

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
        shown.push(step_shown(kind, name, (count >= FIRST_REPEAT).then_some(count)));
    }
    shown
}

/// Where the picker of generators opens: on making a new one.
const NEW_GENERATOR_PLACE: usize = 0;

impl ChainEditor {
    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }

    /// The chain's steps, each (kind of generator, its name).
    fn steps(&self, app: &App) -> Vec<(String, String)> {
        match app.document.get_setlist().get_item(Section::CHAINS, &self.name) {
            Some(Item::Chain(chain)) => chain.get_steps().to_vec(),
            _ => Vec::new(),
        }
    }

    /// Change the chain, as one edit of the set.
    fn change_chain(&self, app: &mut App, change: impl FnOnce(&mut llamatron_model::objects::named::Chain)) {
        change_chain(app, &self.name, change);
    }

    /// Ask for a generator to run: a new one first, then every generator the set has in one list by name, as the Generators
    /// page lists them; then takes the kind and name of the one chosen, and a new one is made first and its editor opened.
    fn pick_generator(&self, app: &mut App, title: &str, then: std::rc::Rc<GeneratorChosen>) {
        let setlist = app.document.get_setlist();
        let mut offered: Vec<(String, String)> = Vec::new();
        for plugin in PLUGINS.iter() {
            for (name, _) in setlist.items(plugin.section) {
                offered.push((plugin.name.to_string(), name.clone()));
            }
        }
        offered.sort_by_key(|(_, name)| llamatron_model::objects::naming::name_order(name));
        let mut shown = vec![messages::MSG_NEW_GENERATOR_CHOICE.to_string()];
        shown.extend(offered.iter().map(|(kind, name)| step_shown(kind, name, None)));
        let mut dialog = ChoiceDialog::new(title, shown, NEW_GENERATOR_PLACE);
        dialog.then = Some(Box::new(move |app: &mut App, answer: &Answer| {
            let Answer::Chosen(place) = answer else { return };
            if *place == NEW_GENERATOR_PLACE {
                let then = then.clone();
                let kinds = listed_kinds().into_iter().filter(|(kind, _, _)| *kind != CHAIN_KIND).collect();
                new_generator(
                    app,
                    kinds,
                    Box::new(move |app: &mut App, kind: &str, name: &str| {
                        then(app, kind, name);
                        app.show_page(editor_of(kind, name));
                    }),
                );
                return;
            }
            let (kind, name) = &offered[*place - 1];
            then(app, kind, name);
        }));
        app.show_page(Box::new(dialog));
    }
}

/// Change a chain by its name, as one edit of the set.
fn change_chain(app: &mut App, name: &str, change: impl FnOnce(&mut llamatron_model::objects::named::Chain)) {
    app.document.change_set(|setlist| {
        if let Some(Item::Chain(chain)) = setlist.get_item_mut(Section::CHAINS, name) {
            change(chain);
        }
    });
}

/// A step as the chain editor shows it: the generator's kind by its page's name, then its name, counted when count is
/// given.
fn step_shown(kind: &str, name: &str, count: Option<usize>) -> String {
    let label = label_of(kind);
    match count {
        Some(count) => named(
            marks::MSG_CHAIN_STEP_AGAIN,
            &[("name", name.into()), ("number", count.into()), ("kind", label.into())],
        ),
        None => named(marks::MSG_CHAIN_STEP_SHOWN, &[("name", name.into()), ("kind", label.into())]),
    }
}

impl Listing for ChainEditor {
    fn follow_renames(&mut self, renames: &crate::history::Renames) {
        let section = Section::CHAINS;
        crate::page::follow_name(&mut self.name, section, renames);
    }

    fn still_exists(&self, app: &App) -> bool {
        crate::page::named_exists(app, Section::CHAINS, &self.name)
    }

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
        vec![Self::bind(&Keys::RENAME)]
    }

    fn can_add(&self) -> bool {
        true
    }

    fn carries_rows(&self) -> bool {
        true
    }

    fn carry_row(&mut self, app: &mut App, place: usize, offset: i64) -> bool {
        if !(0..self.steps(app).len() as i64).contains(&(place as i64 + offset)) {
            return false;
        }
        self.change_chain(app, |chain| {
            chain.move_step(place, offset);
        });
        true
    }

    /// A adds a step at the end, ENTER changes the selected one's generator, C runs it again after itself, Bksp takes it
    /// out, N renames the chain and W opens its statements.
    fn press_row(&mut self, app: &mut App, item: &KeyItem, _key: &str, row: Option<&str>) -> Option<String> {
        let place: Option<usize> = row.and_then(|row| row.parse().ok());
        if item.is(&Keys::ADD) || item.is(&Keys::ADD_HERE) {
            let chain = self.name.clone();
            let added = std::rc::Rc::new(move |app: &mut App, kind: &str, name: &str| {
                change_chain(app, &chain, |held| held.add_step(kind, name));
                let steps = app.document.get_setlist().get_item(Section::CHAINS, &chain).map_or(0, |item| match item {
                    Item::Chain(held) => held.get_steps().len(),
                    _ => 0,
                });
                app.cursor_to(&steps.saturating_sub(1).to_string());
            });
            self.pick_generator(app, messages::MSG_ADD_TO_CHAIN_TITLE, added);
        } else if item.is(&Keys::CHANGE) {
            let place = place?;
            let chain = self.name.clone();
            let changed = std::rc::Rc::new(move |app: &mut App, kind: &str, name: &str| {
                change_chain(app, &chain, |held| held.set_step(place, kind, name));
            });
            self.pick_generator(app, messages::MSG_CHANGE_STEP_TITLE, changed);
        } else if item.is(&Keys::COPY) {
            let place = place?;
            self.change_chain(app, |chain| chain.copy_step(place));
            return Some((place + 1).to_string());
        } else if item.is(&Keys::REMOVE) {
            let place = place?;
            self.change_chain(app, |chain| chain.remove_step(place));
        } else if item.is(&Keys::RENAME) {
            crate::screens::rename::ask_rename(app, Section::CHAINS, &self.name, messages::MSG_RENAME_CHAIN_PROMPT);
        }
        None
    }
}
