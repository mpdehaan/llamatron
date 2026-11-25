// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Generators page (the Python screens/generators/generators_page.py and pages/generators.py): every generator of the
//! set under a heading for its kind, each kind's heading opening and closing it, sorted by name, then + (New).

use crate::app::App;
use crate::drawing::{Align, Style};
use crate::keybindings::{GeneratorsPage as Keys, KeyClass};
use crate::keys::{in_order, KeyItem};
use crate::page::Page;
use crate::screens::list_page::{column_sizes, row_line, shown_around, ListColumn};
use crate::text::Text;
use crate::themes::{self, Colour};
use crate::uses::uses_of;
use llamatron_model::objects::naming::name_order;
use llamatron_model::schema::generated::file_format::{Section, CHAIN_KIND};
use llamatron_model::schema::generated::limits::MAX_NAME_LENGTH;
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_strings::{labels, marks, messages, named};
use std::cell::Cell;

const INDENT: &str = "    ";
const COLUMNS: [ListColumn; 2] = [
    ListColumn {
        heading: labels::Column::SELECT_ANY_GENERATOR,
        width: None,
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::USED,
        width: Some(4),
        align: Align::Right,
    },
];

/// What a row is: a kind's heading, a generator, or + (New).
#[derive(Clone, Debug, PartialEq)]
enum Listed {
    Heading(String),
    Generator(String, String),
    New,
}

/// A generator plugin's label, the word its pages call it by.
pub fn label_of(kind: &str) -> &'static str {
    use llamatron_strings::plugin_texts::*;
    match kind {
        "arp" => arp::MSG_LABEL,
        "chords" => chords::MSG_LABEL,
        "drift" => drift::MSG_LABEL,
        "guitarify" => guitarify::MSG_LABEL,
        "hocket" => hocket::MSG_LABEL,
        "musician" => musician::MSG_LABEL,
        "phrasing" => phrasing::MSG_LABEL,
        "shapes" => shapes::MSG_LABEL,
        "timing" => timing::MSG_LABEL,
        _ => labels::MSG_CHAIN_LABEL,
    }
}

/// Each kind of generator with its section and its label, the chains among them.
pub fn listed_kinds() -> Vec<(&'static str, &'static str, &'static str)> {
    let mut kinds: Vec<(&str, &str, &str)> = PLUGINS.iter().map(|plugin| (plugin.name, plugin.section, label_of(plugin.name))).collect();
    kinds.push((CHAIN_KIND, Section::CHAINS, labels::MSG_CHAIN_LABEL));
    kinds.sort_by_key(|(_, _, label)| label.to_lowercase());
    kinds
}

pub struct GeneratorsPage {
    cursor: Cell<usize>,
    searching: bool,
    typed: String,
    place_before_search: usize,
}

impl GeneratorsPage {
    pub fn new(app: &App) -> GeneratorsPage {
        let page = GeneratorsPage {
            cursor: Cell::new(0),
            searching: false,
            typed: String::new(),
            place_before_search: 0,
        };
        let first = page
            .rows(app)
            .iter()
            .position(|(listed, _)| matches!(listed, Listed::Generator(..)))
            .unwrap_or(0);
        page.cursor.set(first);
        page
    }

    /// The kinds the set has generators of, by their labels.
    fn kinds(&self, app: &App) -> Vec<(&'static str, &'static str, &'static str)> {
        let setlist = app.document.get_setlist();
        listed_kinds()
            .into_iter()
            .filter(|(_, section, _)| !setlist.items(section).is_empty())
            .collect()
    }

    fn rows(&self, app: &App) -> Vec<(Listed, Vec<String>)> {
        let setlist = app.document.get_setlist();
        let mut rows = Vec::new();
        for (kind, section, label) in self.kinds(app) {
            let mut names: Vec<String> = setlist.items(section).iter().map(|(name, _)| name.clone()).collect();
            names.sort_by_key(|name| name_order(name));
            let closed = !app.document.is_generator_type_open(kind) && !self.searching;
            let mark = if closed {
                marks::MSG_SECTION_CLOSED_MARK
            } else {
                marks::MSG_SECTION_OPEN_MARK
            };
            let heading = named(
                labels::MSG_GROUP_HEADING,
                &[("mark", mark.into()), ("name", label.into()), ("count", names.len().into())],
            );
            rows.push((Listed::Heading(kind.to_string()), vec![heading, String::new()]));
            if !closed {
                for name in names {
                    let uses = uses_of(setlist, section, &name).len();
                    rows.push((
                        Listed::Generator(kind.to_string(), name.clone()),
                        vec![format!("{INDENT}{name}"), uses.to_string()],
                    ));
                }
            }
        }
        rows.push((Listed::New, vec![marks::MSG_NEW_ROW.to_string(), String::new()]));
        rows
    }

    fn place(&self, app: &App) -> usize {
        let place = self.cursor.get().min(self.rows(app).len() - 1);
        self.cursor.set(place);
        place
    }

    fn listed(&self, app: &App) -> Listed {
        let rows = self.rows(app);
        rows[self.place(app)].0.clone()
    }

    fn matches(&self, app: &App) -> Vec<usize> {
        let rows = self.rows(app);
        if !self.searching {
            return (0..rows.len()).collect();
        }
        let wanted = self.typed.to_lowercase();
        rows.iter()
            .enumerate()
            .filter(|(_, (_, cells))| cells[0].to_lowercase().contains(&wanted))
            .map(|(place, _)| place)
            .collect()
    }

    fn bind(&self, binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }

    fn search_keys(&self) -> Vec<KeyItem> {
        vec![
            self.bind(&Keys::SEARCH_CANCEL),
            self.bind(&Keys::SELECT).wanting_key(),
            self.bind(&Keys::SEARCH_TYPE).wanting_key(),
            self.bind(&Keys::SEARCH_ERASE),
            self.bind(&Keys::SEARCH_COMPLETE),
            self.bind(&Keys::SEARCH_KEEP),
        ]
    }

    fn jump_type(&self, app: &App, direction: i64) {
        let place = self.cursor.get();
        let headings: Vec<usize> = self
            .rows(app)
            .iter()
            .enumerate()
            .filter(|(_, (listed, _))| matches!(listed, Listed::Heading(_)))
            .map(|(place, _)| place)
            .collect();
        let found = if direction > 0 {
            headings.iter().find(|each| **each > place)
        } else {
            headings.iter().rfind(|each| **each < place)
        };
        if let Some(found) = found {
            self.cursor.set(*found);
        }
    }

    fn move_cursor(&self, app: &mut App, key: &str) {
        let places = self.matches(app);
        if places.is_empty() {
            return;
        }
        let place = self.cursor.get();
        match places.iter().position(|each| *each == place) {
            None => self.cursor.set(places[0]),
            Some(at) => {
                let step: i64 = if key == "up" { -1 } else { 1 };
                self.cursor.set(places[(at as i64 + step).clamp(0, places.len() as i64 - 1) as usize]);
            }
        }
        if self.searching {
            app.say(&named(messages::MSG_SEARCH_STATUS, &[("text", self.typed.as_str().into())]));
        }
    }
}

impl Page for GeneratorsPage {
    fn name(&self) -> &'static str {
        "GeneratorsPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, app: &App) -> Vec<KeyItem> {
        let mut keys = vec![self.bind(&Keys::BACK), self.bind(&Keys::SELECT).wanting_key()];
        match self.listed(app) {
            Listed::Generator(..) => keys.extend(
                [&Keys::EDIT, &Keys::ADD, &Keys::RENAME, &Keys::COPY, &Keys::DELETE]
                    .into_iter()
                    .map(|binding| self.bind(binding)),
            ),
            Listed::Heading(_) => keys.extend([self.bind(&Keys::TOGGLE_TYPE), self.bind(&Keys::ADD)]),
            Listed::New => keys.extend([self.bind(&Keys::ADD_HERE), self.bind(&Keys::ADD)]),
        }
        keys.push(self.bind(&Keys::NEXT_TYPE));
        keys
    }

    fn page_key_table(&self, app: &App) -> Vec<KeyItem> {
        if self.searching {
            return in_order(&Keys::CLASS, self.search_keys());
        }
        let mut table = in_order(&Keys::CLASS, self.keys(app));
        table.push(self.bind(&Keys::SEARCH));
        in_order(&Keys::CLASS, table)
    }

    fn takes_text(&self) -> bool {
        self.searching
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&Keys::BACK) {
            app.go_back();
        } else if item.is(&Keys::SELECT) {
            self.move_cursor(app, key);
        } else if item.is(&Keys::NEXT_TYPE) {
            self.jump_type(app, item.step_of(key).unwrap_or(1));
        } else if item.is(&Keys::TOGGLE_TYPE) {
            if let Listed::Heading(kind) = self.listed(app) {
                let opened = !app.document.is_generator_type_open(&kind);
                app.document.show_generator_type(&kind, opened);
            }
        } else if item.is(&Keys::SEARCH) {
            self.searching = true;
            self.typed.clear();
            self.place_before_search = self.cursor.get();
            app.say(&named(messages::MSG_SEARCH_STATUS, &[("text", "".into())]));
        } else if item.is(&Keys::SEARCH_CANCEL) {
            self.searching = false;
            self.cursor.set(self.place_before_search);
            self.place(app);
        } else if item.is(&Keys::SEARCH_KEEP) {
            self.searching = false;
        } else if item.is(&Keys::EDIT) {
            if let Listed::Generator(kind, name) = self.listed(app) {
                match PLUGINS.iter().find(|plugin| plugin.name == kind) {
                    Some(plugin) => app.show_page(Box::new(crate::screens::field_page::FieldPage::new(
                        crate::screens::generators::plugin_editor::PluginEditor { kind: plugin.name, name },
                    ))),
                    None => app.show_page(Box::new(crate::screens::list_page::ListPage::new(
                        crate::screens::generators::chain_editor::ChainEditor { name },
                    ))),
                }
            }
        }
    }

    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        let place = self.place(app);
        let sizes = column_sizes(&COLUMNS, Some(MAX_NAME_LENGTH as usize + INDENT.len()), width);
        let headings: Vec<String> = COLUMNS.iter().map(|column| column.heading.to_string()).collect();
        let mut lines = vec![row_line(&COLUMNS, &headings, &sizes, Style::BOLD, false), Text::default()];
        let rows = self.rows(app);
        let matches = self.matches(app);
        if matches.is_empty() {
            return lines;
        }
        let at = matches.iter().position(|each| *each == place).unwrap_or(0);
        for index in shown_around(matches.len(), at, height.saturating_sub(2).max(1)) {
            let row = matches[index];
            let (listed, cells) = &rows[row];
            let style = if matches!(listed, Listed::Heading(_)) { Style::BOLD } else { Style::PLAIN };
            lines.push(row_line(&COLUMNS, cells, &sizes, style, row == place));
        }
        lines
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::GENERATORS.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::GENERATORS)
    }
}
