// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The list page (the Python screens/shared/list_page.py and named_list_page.py): a table with a cursor, a + row at the
//! bottom where the page adds, and / searching the rows by their names; a page of a section's named things adds the keys
//! that open, rename, copy, delete, move and sort the selected one.

use crate::app::App;
use crate::drawing::{cursor_mark, fit_aligned, Align, Style};
use crate::keybindings::{Binding, KeyClass, ListPage as Keys};
use crate::keys::{in_order, KeyItem};
use crate::page::{Duration, Page};
use crate::text::Text;
use crate::themes::Colour;
use llamatron_model::schema::generated::limits::MAX_NAME_LENGTH;
use llamatron_strings::{marks, messages, named};
use std::cell::Cell;

/// A column of a list: its heading, its width, or None for the names' room, and how its values stand in it.
pub struct ListColumn {
    pub heading: &'static str,
    pub width: Option<usize>,
    pub align: Align,
}

/// A row: what it is, by its key, and its columns' text.
pub type Row = (String, Vec<String>);

/// What a list page says of itself.
pub trait Listing {
    fn name(&self) -> &'static str;
    fn class(&self) -> &'static KeyClass;
    fn crumbs(&self, app: &App) -> Vec<String>;
    fn theme(&self) -> Option<Colour>;
    fn columns(&self) -> &[ListColumn];
    fn rows(&self, app: &App) -> Vec<Row>;

    fn duration(&self, _app: &App) -> Duration {
        Duration::Nothing
    }

    /// Whether the page adds, with a + row at the bottom.
    fn can_add(&self) -> bool {
        true
    }

    /// The keys for the selected row, which only a row that is something has.
    fn item_keys(&self, _app: &App) -> Vec<KeyItem> {
        Vec::new()
    }

    /// The keys for a row that has keys of its own in place of item_keys, such as a factory groove's, or None.
    fn row_keys(&self, _app: &App, _row: &str) -> Option<Vec<KeyItem>> {
        None
    }

    /// Do what a key of the page's own does to the row of a key, or to the + row, and say the row of the key the cursor goes
    /// to after, where it moves.
    fn press_row(&mut self, app: &mut App, item: &KeyItem, key: &str, row: Option<&str>) -> Option<String>;

    fn row_style(&self, _app: &App, _row: &str) -> &'static str {
        Style::PLAIN
    }

    /// How wide the names' column may grow, or None for as wide as there is room.
    fn name_column_width(&self) -> Option<usize> {
        Some(MAX_NAME_LENGTH as usize)
    }
}

/// The keys a list of a section's named things has for its selected row: ENTER opens it, then rename, copy, delete, move and
/// sort.
pub fn named_item_keys(class: &'static KeyClass, enter: &'static Binding) -> Vec<KeyItem> {
    [enter, &Keys::RENAME, &Keys::COPY, &Keys::DELETE, &Keys::MOVE, &Keys::SORT]
        .into_iter()
        .map(|binding| KeyItem::of(class, binding))
        .collect()
}

pub struct ListPage<L: Listing> {
    pub listing: L,
    cursor: Cell<usize>,
    searching: bool,
    typed: String,
    place_before_search: usize,
}

impl<L: Listing> ListPage<L> {
    pub fn new(listing: L) -> ListPage<L> {
        ListPage {
            listing,
            cursor: Cell::new(0),
            searching: false,
            typed: String::new(),
            place_before_search: 0,
        }
    }

    fn bind(&self, binding: &'static Binding) -> KeyItem {
        KeyItem::of(self.listing.class(), binding)
    }

    /// The rows with the + row at the bottom where the page adds.
    fn rows_with_plus(&self, app: &App) -> Vec<Option<Row>> {
        let mut rows: Vec<Option<Row>> = self.listing.rows(app).into_iter().map(Some).collect();
        if self.listing.can_add() {
            rows.push(None);
        }
        rows
    }

    fn place(&self, app: &App) -> usize {
        let count = self.rows_with_plus(app).len();
        let place = self.cursor.get().min(count.saturating_sub(1));
        self.cursor.set(place);
        place
    }

    /// The selected row's key, or None on the + row.
    fn current(&self, app: &App) -> Option<String> {
        let rows = self.listing.rows(app);
        rows.get(self.place(app)).map(|(key, _)| key.clone())
    }

    /// The places of the rows a search keeps, or of every row and the + row when not searching.
    fn matches(&self, app: &App) -> Vec<usize> {
        if !self.searching {
            return (0..self.rows_with_plus(app).len()).collect();
        }
        let wanted = self.typed.to_lowercase();
        self.listing
            .rows(app)
            .iter()
            .enumerate()
            .filter(|(_, (_, cells))| cells[0].to_lowercase().contains(&wanted))
            .map(|(place, _)| place)
            .collect()
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
            self.show_search(app);
        }
    }

    fn show_search(&self, app: &mut App) {
        app.say(&named(messages::MSG_SEARCH_STATUS, &[("text", self.typed.as_str().into())]));
    }

    fn settle(&self, app: &mut App) {
        let places = self.matches(app);
        if !places.is_empty() && !places.contains(&self.cursor.get()) {
            self.cursor.set(places[0]);
        }
        self.show_search(app);
    }

    fn list_keys(&self, app: &App) -> Vec<KeyItem> {
        let mut keys = vec![self.bind(&Keys::BACK), self.bind(&Keys::SELECT).wanting_key()];
        if self.listing.can_add() {
            keys.push(self.bind(&Keys::ADD));
        }
        if let Some(row) = self.current(app) {
            keys.extend(self.listing.row_keys(app, &row).unwrap_or_else(|| self.listing.item_keys(app)));
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

    fn column_sizes(&self, width: usize) -> Vec<usize> {
        column_sizes(self.listing.columns(), self.listing.name_column_width(), width)
    }

    fn row_line(&self, values: &[String], sizes: &[usize], style: &str, selected: bool) -> Text {
        row_line(self.listing.columns(), values, sizes, style, selected)
    }
}

/// Each column's width: its own where it has one, and what is left for the names', held to a name's room.
pub fn column_sizes(columns: &[ListColumn], name_width: Option<usize>, width: usize) -> Vec<usize> {
    let fixed: usize = columns.iter().filter_map(|column| column.width).map(|size| size + 1).sum();
    let mut flexible = width.saturating_sub(fixed + 3).max(8);
    if let (Some(most), true) = (name_width, columns.len() > 1) {
        flexible = flexible.min(most);
    }
    columns.iter().map(|column| column.width.unwrap_or(flexible)).collect()
}

/// One row's line: the cursor's mark, then each column's value fitted to its width.
pub fn row_line(columns: &[ListColumn], values: &[String], sizes: &[usize], style: &str, selected: bool) -> Text {
    let mut line = Text::styled("", style);
    line.append(cursor_mark(selected), Style::PLAIN);
    for ((value, size), column) in values.iter().zip(sizes).zip(columns) {
        line.append(&format!("{} ", fit_aligned(value, *size, column.align)), Style::PLAIN);
    }
    line
}

/// The run of places a list with room for so many shows, keeping the cursor's near the middle and the list full at either end.
pub fn shown_around(count: usize, at: usize, room: usize) -> std::ops::Range<usize> {
    let start = (at as i64 - (room / 2) as i64).min(count as i64 - room as i64).max(0) as usize;
    start..(start + room).min(count)
}

impl<L: Listing> Page for ListPage<L> {
    fn name(&self) -> &'static str {
        self.listing.name()
    }

    fn class(&self) -> &'static KeyClass {
        self.listing.class()
    }

    fn keys(&self, app: &App) -> Vec<KeyItem> {
        self.list_keys(app)
    }

    fn page_key_table(&self, app: &App) -> Vec<KeyItem> {
        let class = self.listing.class();
        if self.searching {
            return in_order(class, self.search_keys());
        }
        let mut table = in_order(class, self.list_keys(app));
        if self.listing.can_add() && self.current(app).is_none() {
            table.insert(1, self.bind(&Keys::ADD_HERE));
        }
        table.push(self.bind(&Keys::SEARCH));
        in_order(class, table)
    }

    fn takes_text(&self) -> bool {
        self.searching
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
            self.show_search(app);
        } else if item.is(&Keys::SEARCH_CANCEL) {
            self.searching = false;
            self.cursor.set(self.place_before_search);
            self.place(app);
        } else if item.is(&Keys::SEARCH_KEEP) {
            self.searching = false;
        } else if item.is(&Keys::SEARCH_TYPE) {
            self.typed.push_str(if key == "space" { " " } else { key });
            self.settle(app);
        } else if item.is(&Keys::SEARCH_ERASE) {
            self.typed.pop();
            self.settle(app);
        } else {
            let current = self.current(app);
            if let Some(row) = self.listing.press_row(app, item, key, current.as_deref()) {
                if let Some(place) = self.listing.rows(app).iter().position(|(found, _)| *found == row) {
                    self.cursor.set(place);
                }
            }
        }
    }

    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        self.place(app);
        let sizes = self.column_sizes(width);
        let headings: Vec<String> = self.listing.columns().iter().map(|column| column.heading.to_string()).collect();
        let mut lines = vec![self.row_line(&headings, &sizes, Style::BOLD, false), Text::default()];
        let rows = self.rows_with_plus(app);
        let matches = self.matches(app);
        if matches.is_empty() {
            return lines;
        }
        let room = height.saturating_sub(2).max(1);
        let cursor = self.cursor.get();
        let at = matches.iter().position(|place| *place == cursor).unwrap_or(0);
        let start = (at as i64 - (room / 2) as i64).min(matches.len() as i64 - room as i64).max(0) as usize;
        let empty = vec![String::new(); self.listing.columns().len().saturating_sub(1)];
        for place in matches.iter().skip(start).take(room) {
            let (values, style) = match &rows[*place] {
                Some((key, cells)) => (cells.clone(), self.listing.row_style(app, key)),
                None => {
                    let mut plus = vec![marks::MSG_NEW_ROW.to_string()];
                    plus.extend(empty.iter().cloned());
                    (plus, Style::PLAIN)
                }
            };
            lines.push(self.row_line(&values, &sizes, style, *place == cursor));
        }
        lines
    }

    fn crumbs(&self, app: &App) -> Vec<String> {
        self.listing.crumbs(app)
    }

    fn theme(&self) -> Option<Colour> {
        self.listing.theme()
    }

    fn duration(&self, app: &App) -> Duration {
        self.listing.duration(app)
    }
}
