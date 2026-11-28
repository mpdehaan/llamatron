// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Generators page: every generator of the set in one list sorted by name, each with its kind and how often it is used,
//! then + (New). A set's generators and chains share one list of names, so no two rows share a name.

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

/// The KIND column's width: the longest kind's label and a space.
const KIND_WIDTH: usize = 12;
const COLUMNS: [ListColumn; 3] = [
    ListColumn {
        heading: labels::Column::SELECT_ANY_GENERATOR,
        width: None,
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::KIND,
        width: Some(KIND_WIDTH),
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::USED,
        width: Some(4),
        align: Align::Right,
    },
];

/// What a row is: a generator, by its kind and name, or + (New).
#[derive(Clone, Debug, PartialEq)]
enum Listed {
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
    /// The generator, by kind and name, that the cursor goes to when the page is next drawn, such as one just renamed.
    going_to: std::rc::Rc<std::cell::RefCell<Option<(String, String)>>>,
    searching: bool,
    typed: String,
    place_before_search: usize,
}

/// The editor of a generator of a kind: a chain's list of steps, or a plugin's settings page.
pub fn editor_of(kind: &str, name: &str) -> Box<dyn Page> {
    match PLUGINS.iter().find(|plugin| plugin.name == kind) {
        Some(plugin) => Box::new(crate::screens::field_page::FieldPage::new(
            crate::screens::generators::plugin_editor::PluginEditor {
                kind: plugin.name,
                name: name.to_string(),
            },
        )),
        None => Box::new(crate::screens::list_page::ListPage::new(
            crate::screens::generators::chain_editor::ChainEditor { name: name.to_string() },
        )),
    }
}

/// A name the tracker makes up from a label: lowercase, an underscore where a space would be.
fn suggested_word(label: &str) -> String {
    label.trim().to_lowercase().replace(' ', "_")
}

/// What takes a generator chosen or made, by its kind and name.
pub type GeneratorChosen = dyn Fn(&mut App, &str, &str);

/// Ask which of some kinds of generator to make, each (kind, section, label), make one named after the kind and numbered,
/// and hand its kind and name on.
pub fn new_generator(app: &mut App, kinds: Vec<(&'static str, &'static str, &'static str)>, then: Box<GeneratorChosen>) {
    let options = kinds.iter().map(|(_, _, label)| label.to_string()).collect();
    let mut dialog = crate::screens::dialogs::ChoiceDialog::new(messages::MSG_NEW_GENERATOR_KIND_TITLE, options, 0);
    dialog.then = Some(Box::new(move |app: &mut App, answer: &crate::screens::dialogs::Answer| {
        let crate::screens::dialogs::Answer::Chosen(place) = answer else { return };
        let (kind, section, label) = kinds[*place];
        let name = app.document.new_name(section, &suggested_word(label));
        match app.document.add_generator(section, &name) {
            Ok(()) => then(app, kind, &name),
            Err(problem) => app.refuse(&problem),
        }
    }));
    app.show_page(Box::new(dialog));
}

impl GeneratorsPage {
    /// Ask which type of generator to make, make one, put the cursor on it and open it.
    fn add(&self, app: &mut App) {
        // Which generator the cursor goes to is known only once the dialog has made it.
        let going_to = self.going_to.clone();
        new_generator(
            app,
            listed_kinds(),
            Box::new(move |app: &mut App, kind: &str, name: &str| {
                *going_to.borrow_mut() = Some((kind.to_string(), name.to_string()));
                app.show_page(editor_of(kind, name));
            }),
        );
    }

    /// Rename, copy or delete the selected generator: a copy says what it is called and takes the cursor, and a delete asks
    /// first, saying which chains and lists it is taken out of.
    fn edit_generator(&self, app: &mut App, item: &KeyItem, kind: &str, name: &str) {
        let Some(&(_, section, label)) = listed_kinds().iter().find(|(found, _, _)| *found == kind) else {
            return;
        };
        if item.is(&Keys::RENAME) {
            let prompt = named(messages::MSG_RENAME_GENERATOR_PROMPT, &[("label", label.into())]);
            crate::screens::rename::ask_rename(app, section, name, &prompt);
        } else if item.is(&Keys::COPY) {
            match app.document.copy_named(section, name) {
                Ok(new) => {
                    app.say(&named(messages::MSG_COPIED_TO, &[("name", new.as_str().into())]));
                    *self.going_to.borrow_mut() = Some((kind.to_string(), new));
                }
                Err(problem) => app.refuse(&problem),
            }
        } else {
            let what = named(
                llamatron_strings::legends::MSG_GENERATOR_WHAT,
                &[("label", label.into()), ("name", name.into())],
            );
            let mut lines = Vec::new();
            let uses = uses_of(app.document.get_setlist(), section, name);
            if !uses.is_empty() {
                lines.push(messages::MSG_TAKEN_OUT_OF.to_string());
                lines.extend(uses.iter().take(MOST_USES_SHOWN).cloned());
                if uses.len() > MOST_USES_SHOWN {
                    lines.push(named(
                        llamatron_strings::errors::ERR_AND_MORE,
                        &[("count", (uses.len() - MOST_USES_SHOWN).into())],
                    ));
                }
            }
            let question = named(messages::MSG_DELETE_QUESTION, &[("what", what.as_str().into())]);
            let name = name.to_string();
            let confirm = crate::screens::dialogs::ConfirmDialog::new(&question, lines, false, true).then(Box::new(
                move |app: &mut App, _: &crate::screens::dialogs::Answer| {
                    if let Err(problem) = app.document.delete_named(section, &name) {
                        app.refuse(&problem);
                    }
                },
            ));
            app.show_page(Box::new(confirm));
        }
    }

    pub fn new(app: &App) -> GeneratorsPage {
        let page = GeneratorsPage {
            cursor: Cell::new(0),
            going_to: std::rc::Rc::new(std::cell::RefCell::new(None)),
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

    /// Every generator of the set, sorted by name, then the + row.
    fn rows(&self, app: &App) -> Vec<(Listed, Vec<String>)> {
        let setlist = app.document.get_setlist();
        let mut generators: Vec<(&str, &str, &str, String)> = Vec::new();
        for (kind, section, label) in listed_kinds() {
            for (name, _) in setlist.items(section) {
                generators.push((kind, section, label, name.clone()));
            }
        }
        generators.sort_by_key(|(.., name)| name_order(name));
        let mut rows: Vec<(Listed, Vec<String>)> = generators
            .into_iter()
            .map(|(kind, section, label, name)| {
                let uses = uses_of(setlist, section, &name).len();
                let cells = vec![name.clone(), label.to_string(), uses.to_string()];
                (Listed::Generator(kind.to_string(), name), cells)
            })
            .collect();
        rows.push((Listed::New, vec![marks::MSG_NEW_ROW.to_string(), String::new(), String::new()]));
        rows
    }

    fn place(&self, app: &App) -> usize {
        if let Some((kind, name)) = self.going_to.borrow_mut().take() {
            let wanted = Listed::Generator(kind, name);
            if let Some(found) = self.rows(app).iter().position(|(listed, _)| *listed == wanted) {
                self.cursor.set(found);
            }
        }
        let place = self.cursor.get().min(self.rows(app).len() - 1);
        self.cursor.set(place);
        place
    }

    fn listed(&self, app: &App) -> Listed {
        let rows = self.rows(app);
        rows[self.place(app)].0.clone()
    }

    /// After a key changed what a search looks for, keep the cursor among the rows it finds, and show what was typed.
    fn settle_search(&self, app: &mut App) {
        let matches = self.matches(app);
        if !matches.is_empty() && !matches.contains(&self.cursor.get()) {
            self.cursor.set(matches[0]);
        }
        app.say(&named(messages::MSG_SEARCH_STATUS, &[("text", self.typed.as_str().into())]));
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

/// How many of the chains and lists a deleted generator is taken out of its question lists.
const MOST_USES_SHOWN: usize = 5;

impl Page for GeneratorsPage {
    /// The + row, or a generator by its kind, so that each kind's editor is reached.
    fn place_kind(&self, app: &App) -> String {
        // A search offers keys of its own, so a row found by one is a place apart from the same row otherwise.
        if self.searching {
            return "searching".to_string();
        }
        match self.listed(app) {
            Listed::Generator(kind, _) => format!("generator {kind}"),
            Listed::New => "plus".to_string(),
        }
    }

    /// After a rename made here, the cursor goes to the generator under its new name.
    fn follow_renames(&mut self, renames: &crate::history::Renames) {
        if !renames.made_here {
            return;
        }
        for (section, _, new) in &renames.named {
            if let Some((kind, _, _)) = listed_kinds().into_iter().find(|(_, found, _)| found == section) {
                *self.going_to.borrow_mut() = Some((kind.to_string(), new.clone()));
            }
        }
    }

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
            Listed::New => keys.extend([self.bind(&Keys::ADD_HERE), self.bind(&Keys::ADD)]),
        }
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

    /// A character typed into the search, which keeps the rows holding what was typed.
    fn type_text(&mut self, app: &mut App, character: char) {
        self.typed.push(character);
        self.settle_search(app);
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&Keys::BACK) {
            app.go_back();
        } else if item.is(&Keys::SELECT) {
            self.move_cursor(app, key);
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
            // The generator found stays under the cursor once every row shows again.
            let found = self.listed(app);
            self.searching = false;
            if let Listed::Generator(kind, name) = found {
                *self.going_to.borrow_mut() = Some((kind, name));
                self.place(app);
            }
        } else if item.is(&Keys::SEARCH_ERASE) {
            self.typed.pop();
            self.settle_search(app);
        } else if item.is(&Keys::SEARCH_COMPLETE) {
            let rows = self.rows(app);
            let found: Vec<String> = self
                .matches(app)
                .iter()
                .filter_map(|place| rows.get(*place))
                .map(|(_, cells)| cells[0].trim().to_string())
                .collect();
            self.typed = crate::screens::dialogs::completed_from(&found, &self.typed);
            self.settle_search(app);
        } else if item.is(&Keys::ADD) || item.is(&Keys::ADD_HERE) {
            self.add(app);
        } else if item.is(&Keys::RENAME) || item.is(&Keys::COPY) || item.is(&Keys::DELETE) {
            if let Listed::Generator(kind, name) = self.listed(app) {
                self.edit_generator(app, item, &kind, &name);
            }
        } else if item.is(&Keys::EDIT) {
            if let Listed::Generator(kind, name) = self.listed(app) {
                app.show_page(editor_of(&kind, &name));
            }
        }
    }

    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        let place = self.place(app);
        let sizes = column_sizes(&COLUMNS, Some(MAX_NAME_LENGTH as usize), width);
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
            let (_, cells) = &rows[row];
            lines.push(row_line(&COLUMNS, cells, &sizes, Style::PLAIN, row == place));
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

#[cfg(test)]
mod tests {
    use super::*;
    use llamatron_model::objects::setlist::Setlist;

    /// A set of one song with generators of three kinds, named so that their order by name mixes the kinds.
    const MIXED_KINDS_SET: &str = include_str!("../../../tests/data/mixed_kinds_set.yml");

    fn mixed_kinds_app() -> App {
        let setlist = Setlist::read_text(MIXED_KINDS_SET).expect("the scenario's set is valid");
        App::new(crate::document::Document::new(setlist, None))
    }

    /// Every generator is in one list by name, ignoring case, whatever its kind, each row naming its kind, then the + row.
    #[test]
    fn the_page_lists_every_generator_by_name_with_its_kind() {
        let app = mixed_kinds_app();
        let page = GeneratorsPage::new(&app);
        let rows = page.rows(&app);
        let shown: Vec<(&str, &str)> = rows.iter().map(|(_, cells)| (cells[0].as_str(), cells[1].as_str())).collect();
        let arpeggiator = label_of("arp");
        let expected = vec![
            ("alpha", labels::MSG_CHAIN_LABEL),
            ("Bounce", arpeggiator),
            ("climb", label_of("drift")),
            ("zip", arpeggiator),
            (marks::MSG_NEW_ROW, ""),
        ];
        assert_eq!(shown, expected);
    }
}
