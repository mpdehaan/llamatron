// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Patterns page (the Python screens/pattern/patterns_page.py and pages/pattern_list.py): every pattern of the set in a
//! tab of its group, a tab per group sorted by name, then Ungrouped while a pattern is in no group, then + New; each group's
//! patterns sorted by name, with + (New) under them. Tab goes between the row of tabs and the list.

#[path = "patterns_edits.rs"]
mod edits;
use crate::app::App;
use crate::drawing::{Align, Style};
use crate::forms::drawing::{boxed_tabs, inner_width};
use crate::forms::tab_box::Tab;
use crate::keybindings::{KeyClass, PatternsPage as Keys};
use crate::keys::{in_order, KeyItem};
use crate::page::{clock_exact, Page};
use crate::screens::list_page::{column_sizes, row_line, shown_around, ListColumn};
use crate::text::Text;
use crate::themes::{self, Colour};
use crate::uses::uses_of;
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::naming::name_order;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::{PatternSetting, Section};
use llamatron_model::schema::generated::limits::MAX_NAME_LENGTH;
use llamatron_strings::{labels, marks, messages, named};

const COLUMNS: [ListColumn; 5] = [
    ListColumn {
        heading: labels::Column::SELECT_PATTERN,
        width: None,
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::TYPE,
        width: Some(5),
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::STEPS,
        width: Some(5),
        align: Align::Right,
    },
    ListColumn {
        heading: labels::Column::TIME,
        width: Some(6),
        align: Align::Right,
    },
    ListColumn {
        heading: labels::Column::USED,
        width: Some(4),
        align: Align::Right,
    },
];
/// The blank lines inside the box above and below the list, and the row of tabs' lines.
const INSIDE_ABOVE: usize = 1;
const INSIDE_BELOW: usize = 1;
const TAB_ROW_LINES: usize = 3;

/// A tab of the page: a group's, Ungrouped, or + New.
#[derive(Clone, Debug, PartialEq)]
enum PatternTab {
    Group(String),
    Ungrouped,
    New,
}

/// What a row is: a pattern, the + (New) row of a group, or the button that makes a group.
#[derive(Clone, Debug, PartialEq)]
enum Listed {
    Pattern(String),
    NewPattern(String),
    NewGroup,
}

pub struct PatternsPage {
    cursor: std::cell::Cell<usize>,
    /// The groups made on the page that hold no pattern yet, shared with the dialogs that make and rename them.
    new_groups: std::rc::Rc<std::cell::RefCell<Vec<String>>>,
    /// The pattern the cursor goes to when the page is next drawn, such as one just renamed here.
    going_to: std::cell::RefCell<Option<String>>,
    on_tabs: bool,
    searching: bool,
    typed: String,
    place_before_search: usize,
}

fn group_of(item: &Item) -> Option<String> {
    match item {
        Item::Pattern(pattern) => pattern.get_written(PatternSetting::GROUP).and_then(Data::as_str).map(str::to_string),
        _ => None,
    }
}

impl PatternsPage {
    pub fn new(app: &App) -> PatternsPage {
        let page = PatternsPage {
            cursor: std::cell::Cell::new(0),
            new_groups: std::rc::Rc::new(std::cell::RefCell::new(Vec::new())),
            going_to: std::cell::RefCell::new(None),
            on_tabs: false,
            searching: false,
            typed: String::new(),
            place_before_search: 0,
        };
        page.cursor.set(page.first_pattern_place(app));
        page
    }

    fn groups(&self, app: &App) -> Vec<String> {
        let mut groups: Vec<String> = app
            .document
            .get_setlist()
            .items(Section::PATTERNS)
            .iter()
            .filter_map(|(_, item)| group_of(item))
            .collect();
        for made in self.groups_made_here() {
            if !groups.contains(&made) {
                groups.push(made);
            }
        }
        groups.sort_by_key(|group| name_order(group));
        groups.dedup();
        groups
    }

    fn patterns_in(&self, app: &App, group: Option<&str>) -> Vec<String> {
        let mut names: Vec<String> = app
            .document
            .get_setlist()
            .items(Section::PATTERNS)
            .iter()
            .filter(|(_, item)| group_of(item).as_deref() == group)
            .map(|(name, _)| name.clone())
            .collect();
        names.sort_by_key(|name| name_order(name));
        names
    }

    fn tabs(&self, app: &App) -> Vec<PatternTab> {
        let mut tabs: Vec<PatternTab> = self.groups(app).into_iter().map(PatternTab::Group).collect();
        if !self.patterns_in(app, None).is_empty() {
            tabs.push(PatternTab::Ungrouped);
        }
        tabs.push(PatternTab::New);
        tabs
    }

    fn tab_label(tab: &PatternTab) -> String {
        match tab {
            PatternTab::Group(group) => group.clone(),
            PatternTab::Ungrouped => labels::MSG_UNGROUPED.to_string(),
            PatternTab::New => labels::MSG_NEW_GROUP_TAB.to_string(),
        }
    }

    fn chosen(&self, app: &App) -> PatternTab {
        let tabs = self.tabs(app);
        let held = app.session.chosen_tabs.get("PatternsPage");
        tabs.iter()
            .find(|tab| Some(&Self::tab_label(tab)) == held)
            .cloned()
            .unwrap_or_else(|| tabs[0].clone())
    }

    fn pattern_rows(&self, app: &App, group: Option<&str>) -> Vec<(Listed, Vec<String>)> {
        let setlist = app.document.get_setlist();
        let song = app.document.song();
        let tempo = llamatron_model::schema::checking::number(&song.get_tempo()).unwrap_or(Rational::whole(120));
        let mut rows = Vec::new();
        for name in self.patterns_in(app, group) {
            let Some(pattern) = setlist.get_pattern(&name) else { continue };
            let kind = if pattern.is_drum() { labels::MSG_DRUM_KIND } else { labels::MSG_NOTES_KIND };
            let seconds = setlist.get_pattern_length(pattern) * Rational::whole(240) / tempo;
            let uses = uses_of(setlist, Section::PATTERNS, &name).len();
            rows.push((
                Listed::Pattern(name.clone()),
                vec![name, kind.to_string(), pattern.get_steps().to_string(), clock_exact(seconds), uses.to_string()],
            ));
        }
        rows
    }

    fn one_cell(text: &str) -> Vec<String> {
        let mut cells = vec![text.to_string()];
        cells.extend(std::iter::repeat_n(String::new(), COLUMNS.len() - 1));
        cells
    }

    fn rows(&self, app: &App) -> Vec<(Listed, Vec<String>)> {
        if self.searching {
            return self
                .tabs(app)
                .iter()
                .flat_map(|tab| {
                    let group = match tab {
                        PatternTab::Group(group) => Some(group.as_str()),
                        _ => None,
                    };
                    self.pattern_rows(app, group)
                })
                .collect();
        }
        match self.chosen(app) {
            PatternTab::New => vec![(Listed::NewGroup, Self::one_cell(labels::MSG_NEW_GROUP_BUTTON))],
            PatternTab::Ungrouped => self.pattern_rows(app, None),
            PatternTab::Group(group) => {
                let mut rows = self.pattern_rows(app, Some(&group));
                rows.push((Listed::NewPattern(group), Self::one_cell(marks::MSG_NEW_ROW)));
                rows
            }
        }
    }

    fn first_pattern_place(&self, app: &App) -> usize {
        self.rows(app).iter().position(|(listed, _)| matches!(listed, Listed::Pattern(_))).unwrap_or(0)
    }

    fn place(&self, app: &App) -> usize {
        if let Some(name) = self.going_to.borrow_mut().take() {
            if let Some(found) = self.rows(app).iter().position(|(listed, _)| *listed == Listed::Pattern(name.clone())) {
                self.cursor.set(found);
            }
        }
        let place = self.cursor.get().min(self.rows(app).len().saturating_sub(1));
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

    fn step_tab(&self, app: &mut App, direction: i64) {
        let tabs = self.tabs(app);
        let here = tabs.iter().position(|tab| *tab == self.chosen(app)).unwrap_or(0);
        let place = (here as i64 + direction).clamp(0, tabs.len() as i64 - 1) as usize;
        app.session.chosen_tabs.insert("PatternsPage".to_string(), Self::tab_label(&tabs[place]));
        self.cursor.set(self.first_pattern_place(app));
    }

    fn tab_row_keys(&self, app: &App) -> Vec<KeyItem> {
        let mut keys = vec![self.bind(&Keys::ALONG_TABS), self.bind(&Keys::INTO_TAB)];
        match self.chosen(app) {
            PatternTab::New => keys.push(self.bind(&Keys::NEW_GROUP)),
            PatternTab::Ungrouped => {}
            PatternTab::Group(_) => keys.extend(
                [&Keys::ADD, &Keys::RENAME, &Keys::COPY, &Keys::UNGROUP]
                    .into_iter()
                    .map(|binding| self.bind(binding)),
            ),
        }
        keys
    }

    fn pattern_keys(&self, app: &App, name: &str) -> Vec<KeyItem> {
        let mut keys = vec![self.bind(&Keys::EDIT), self.bind(&Keys::GROUP)];
        let grouped = app.document.get_setlist().get_item(Section::PATTERNS, name).and_then(group_of).is_some();
        if grouped {
            keys.push(self.bind(&Keys::ADD));
        }
        keys.extend([&Keys::RENAME, &Keys::COPY, &Keys::DELETE].into_iter().map(|binding| self.bind(binding)));
        match crate::screens::listening::pattern_listen_key(app, name) {
            Some(crate::screens::listening::ListenKey::Listen) => keys.push(self.bind(&Keys::LISTEN)),
            Some(crate::screens::listening::ListenKey::Stop) => keys.push(self.bind(&Keys::STOP_LISTENING)),
            None => {}
        }
        keys
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

    fn move_cursor(&mut self, app: &mut App, key: &str) {
        let matches = self.matches(app);
        if self.on_tabs {
            if key != "up" && !matches.is_empty() {
                self.on_tabs = false;
                self.cursor.set(matches[0]);
            }
            return;
        }
        if key == "up" && !self.searching && matches.first() == Some(&self.cursor.get()) {
            self.on_tabs = true;
            return;
        }
        let place = self.cursor.get();
        match matches.iter().position(|each| *each == place) {
            None => self.cursor.set(matches.first().copied().unwrap_or(0)),
            Some(at) => {
                let step: i64 = if key == "up" { -1 } else { 1 };
                self.cursor.set(matches[(at as i64 + step).clamp(0, matches.len() as i64 - 1) as usize]);
            }
        }
        if self.searching {
            app.say(&named(messages::MSG_SEARCH_STATUS, &[("text", self.typed.as_str().into())]));
        }
    }
}

impl Page for PatternsPage {
    fn go_to_row(&mut self, app: &App, row: &str) {
        self.put_cursor_at(app, row);
    }

    /// After a rename made here, the cursor goes to the pattern under its new name.
    fn follow_renames(&mut self, renames: &crate::history::Renames) {
        if !renames.made_here {
            return;
        }
        if let Some((_, _, new)) = renames.named.iter().find(|(section, _, _)| section == Section::PATTERNS) {
            *self.going_to.borrow_mut() = Some(new.clone());
        }
    }

    fn name(&self) -> &'static str {
        "PatternsPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, app: &App) -> Vec<KeyItem> {
        let mut keys = vec![self.bind(&Keys::BACK), self.bind(&Keys::SELECT).wanting_key()];
        if self.on_tabs {
            keys.extend(self.tab_row_keys(app));
            keys.push(self.bind(&Keys::TAB_PAGES));
            return keys;
        }
        match self.listed(app) {
            Listed::Pattern(name) => keys.extend(self.pattern_keys(app, &name)),
            Listed::NewPattern(_) => keys.push(self.bind(&Keys::NEW_PATTERN)),
            Listed::NewGroup => keys.push(self.bind(&Keys::NEW_GROUP)),
        }
        keys.push(self.bind(&Keys::TO_TABS));
        keys.push(self.bind(&Keys::TAB_PAGES));
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
        let direction = item.step_of(key).unwrap_or(0);
        if item.is(&Keys::BACK) {
            app.go_back();
        } else if item.is(&Keys::SELECT) {
            self.move_cursor(app, key);
        } else if item.is(&Keys::ALONG_TABS) || item.is(&Keys::TAB_PAGES) {
            self.step_tab(app, direction);
        } else if item.is(&Keys::TO_TABS) {
            self.on_tabs = true;
        } else if item.is(&Keys::INTO_TAB) {
            self.on_tabs = false;
            self.cursor.set(self.first_pattern_place(app));
        } else if item.is(&Keys::SEARCH) {
            // The search starts from the row the cursor is on, found again among every group's rows, which it lists.
            let before = self.listed(app);
            self.on_tabs = false;
            self.place_before_search = self.cursor.get();
            self.searching = true;
            self.typed.clear();
            if let Some(place) = self.rows(app).iter().position(|(listed, _)| *listed == before) {
                self.cursor.set(place);
            }
            self.place(app);
            app.say(&named(messages::MSG_SEARCH_STATUS, &[("text", "".into())]));
        } else if item.is(&Keys::SEARCH_CANCEL) {
            self.searching = false;
            self.cursor.set(self.place_before_search);
            self.place(app);
        } else if item.is(&Keys::SEARCH_KEEP) {
            self.searching = false;
        } else if self.press_edit(app, item) {
        } else if item.is(&Keys::EDIT) {
            if let Listed::Pattern(name) = self.listed(app) {
                app.show_page(crate::screens::pattern::open_pattern(&name));
            }
        } else if item.is(&Keys::LISTEN) {
            if let Listed::Pattern(name) = self.listed(app) {
                crate::screens::listening::listen_to_pattern(app, &name);
            }
        } else if item.is(&Keys::STOP_LISTENING) {
            crate::screens::listening::stop_listening_to_pattern(app);
        }
    }

    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        let inner = inner_width(width);
        let room = height.saturating_sub(TAB_ROW_LINES + INSIDE_ABOVE + INSIDE_BELOW + 1);
        let sizes = column_sizes(&COLUMNS, Some(MAX_NAME_LENGTH as usize), inner);
        let headings: Vec<String> = COLUMNS.iter().map(|column| column.heading.to_string()).collect();
        let mut rows = vec![row_line(&COLUMNS, &headings, &sizes, Style::BOLD, false), Text::default()];
        let listed = self.rows(app);
        let matches = self.matches(app);
        let cursor = self.place(app);
        if !matches.is_empty() {
            let at = matches.iter().position(|place| *place == cursor).unwrap_or(0);
            let button = themes::text_style(themes::PATTERNS);
            for index in shown_around(matches.len(), at, room.saturating_sub(2).max(1)) {
                let place = matches[index];
                let (what, cells) = &listed[place];
                let style = if matches!(what, Listed::Pattern(_)) { Style::PLAIN } else { button.as_str() };
                rows.push(row_line(&COLUMNS, cells, &sizes, style, !self.on_tabs && place == cursor));
            }
        }
        let mut lines = vec![Text::default(); INSIDE_ABOVE];
        lines.extend(rows);
        lines.extend(vec![Text::default(); INSIDE_BELOW]);
        let tabs = self.tabs(app);
        let chosen = self.chosen(app);
        let shown: Vec<Tab> = tabs.iter().map(|tab| Tab::new(&Self::tab_label(tab), Vec::new())).collect();
        let place = tabs.iter().position(|tab| *tab == chosen).unwrap_or(0);
        boxed_tabs(&shown, place, width, self.on_tabs, &lines)
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::PATTERNS.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::PATTERNS)
    }
}
