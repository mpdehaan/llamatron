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
    /// Keep showing the same thing after a step renamed it, and say whether the thing is still in the set (the page's own).
    fn follow_renames(&mut self, _renames: &crate::history::Renames) {}
    fn still_exists(&self, _app: &App) -> bool {
        true
    }

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

    /// What the theme's stripe says, where that is more than the page's own crumb in capitals.
    fn caption(&self, _app: &App) -> Option<String> {
        None
    }

    /// The keys the page has wherever its cursor is, after its rows' own.
    fn always_keys(&self, _app: &App) -> Vec<KeyItem> {
        Vec::new()
    }

    fn row_style(&self, _app: &App, _row: &str) -> &'static str {
        Style::PLAIN
    }

    /// Lines the page shows over its table, such as the Open page's folder.
    fn lines_above(&self, _app: &App) -> Vec<Text> {
        Vec::new()
    }

    /// The section of the set the page lists, with the words its prompts and questions use for one of its things, where
    /// the page renames, copies, deletes, moves and sorts them as every list of named things does.
    fn named(&self) -> Option<NamedWords> {
        None
    }

    /// Whether Move mode carries the page's rows, which are not a section's named things, such as a chain's steps: carry_row
    /// moves the row at a place one place up or down, and says whether it moved.
    fn carries_rows(&self) -> bool {
        false
    }
    fn carry_row(&mut self, _app: &mut App, _place: usize, _offset: i64) -> bool {
        false
    }

    /// Why the selected thing cannot be deleted at all, such as the set's last song, or None.
    fn delete_refusal(&self, _app: &App) -> Option<&'static str> {
        None
    }

    /// How wide the names' column may grow, or None for as wide as there is room.
    fn name_column_width(&self) -> Option<usize> {
        Some(MAX_NAME_LENGTH as usize)
    }
}

/// What a list of a section's named things says of them: its section, the title of the prompt that renames one, and the
/// words for one in a question, each a template taking the name.
pub struct NamedWords {
    pub section: &'static str,
    pub rename_prompt: &'static str,
    pub what: &'static str,
}

/// How many of the things that still use an item the refusal to delete it lists.
const MOST_USES_SHOWN: usize = 5;

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
    /// Move mode: whether M has picked up the cursor's row, and whether it has been carried yet, so that one move is one
    /// undo step.
    moving: bool,
    carried: bool,
}

impl<L: Listing> ListPage<L> {
    pub fn new(listing: L) -> ListPage<L> {
        ListPage {
            listing,
            cursor: Cell::new(0),
            searching: false,
            typed: String::new(),
            place_before_search: 0,
            moving: false,
            carried: false,
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
        keys.extend(self.listing.always_keys(app));
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

    /// Do what the keys every list of named things has do, and say whether the key was one: Move mode's drop and carry, then
    /// rename, copy, delete, move and sort for the selected thing.
    fn press_named(&mut self, app: &mut App, item: &KeyItem, key: &str) -> bool {
        if self.moving {
            if item.is(&Keys::DROP) {
                self.moving = false;
            } else if item.is(&Keys::CARRY) {
                let offset = item.step_of(key).unwrap_or(1);
                self.carry(app, offset);
            }
            return true;
        }
        if item.is(&Keys::MOVE) && self.listing.carries_rows() && self.current(app).is_some() {
            self.moving = true;
            self.carried = false;
            self.say_moving(app);
            return true;
        }
        let (Some(words), Some(name)) = (self.listing.named(), self.current(app)) else {
            return false;
        };
        if item.is(&Keys::RENAME) {
            self.rename(app, &words, &name);
        } else if item.is(&Keys::COPY) {
            match app.document.copy_named(words.section, &name) {
                Ok(new) => {
                    app.say(&named(messages::MSG_COPIED_TO, &[("name", new.as_str().into())]));
                    self.put_cursor_on(app, &new);
                }
                Err(problem) => app.refuse(&problem),
            }
        } else if item.is(&Keys::DELETE) {
            self.delete(app, &words, &name);
        } else if item.is(&Keys::MOVE) {
            self.moving = true;
            self.carried = false;
            self.say_moving(app);
        } else if item.is(&Keys::SORT) {
            match app.document.sort_named(words.section) {
                Ok(()) => self.put_cursor_on(app, &name),
                Err(problem) => app.refuse(&problem),
            }
        } else {
            return false;
        }
        true
    }

    /// Ask for the selected thing's new name, which cannot be empty or another's.
    fn rename(&self, app: &mut App, words: &NamedWords, name: &str) {
        crate::screens::rename::ask_rename(app, words.section, name, words.rename_prompt);
    }

    /// Delete the selected thing after asking, or say what still uses it.
    fn delete(&self, app: &mut App, words: &NamedWords, name: &str) {
        if let Some(refusal) = self.listing.delete_refusal(app) {
            app.refuse(refusal);
            return;
        }
        let what = named(words.what, &[("name", name.into())]);
        let uses = crate::uses::uses_of(app.document.get_setlist(), words.section, name);
        if !uses.is_empty() {
            let mut lines = vec![named(llamatron_strings::errors::ERR_STILL_USED, &[("what", what.as_str().into())])];
            lines.extend(uses.iter().take(MOST_USES_SHOWN).cloned());
            if uses.len() > MOST_USES_SHOWN {
                lines.push(named(
                    llamatron_strings::errors::ERR_AND_MORE,
                    &[("count", (uses.len() - MOST_USES_SHOWN).into())],
                ));
            }
            app.show_page(Box::new(crate::screens::dialogs::MessageDialog::new(
                llamatron_strings::errors::ERR_CANT_DELETE_TITLE,
                lines,
            )));
            return;
        }
        let section = words.section;
        let name = name.to_string();
        let question = named(messages::MSG_DELETE_QUESTION, &[("what", what.as_str().into())]);
        let confirm = crate::screens::dialogs::ConfirmDialog::new(&question, Vec::new(), false, true).then(Box::new(
            move |app: &mut App, _: &crate::screens::dialogs::Answer| {
                if let Err(problem) = app.document.delete_named(section, &name) {
                    app.refuse(&problem);
                }
            },
        ));
        app.show_page(Box::new(confirm));
    }

    /// Carry the picked-up row one place up or down, every carry of one move making one undo step.
    fn carry(&mut self, app: &mut App, offset: i64) {
        if self.listing.carries_rows() {
            if self.carried {
                app.document.continue_edit();
            }
            self.carried = true;
            let place = self.cursor.get();
            if self.listing.carry_row(app, place, offset) {
                self.cursor.set((place as i64 + offset).max(0) as usize);
            }
            self.say_moving(app);
            return;
        }
        let (Some(words), Some(name)) = (self.listing.named(), self.current(app)) else {
            return;
        };
        let Some(own) = app.document.get_setlist().items(words.section).iter().position(|(each, _)| *each == name) else {
            return;
        };
        if self.carried {
            app.document.continue_edit();
        }
        self.carried = true;
        if app.document.move_named(words.section, own, offset) {
            self.cursor.set((self.cursor.get() as i64 + offset).max(0) as usize);
        }
        self.say_moving(app);
    }

    /// Say what Move mode carries.
    fn say_moving(&self, app: &mut App) {
        let rows = self.listing.rows(app);
        let shown = rows.get(self.cursor.get()).map(|(_, cells)| cells[0].clone()).unwrap_or_default();
        let row = named(messages::MSG_MOVING_ROW, &[("name", shown.as_str().into())]);
        app.say(&named(messages::MSG_MOVING, &[("what", row.as_str().into())]));
    }

    /// Put the cursor on the row of a name.
    fn put_cursor_on(&self, app: &App, name: &str) {
        if let Some(place) = self.listing.rows(app).iter().position(|(key, _)| key == name) {
            self.cursor.set(place);
        }
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

/// A row Move mode carries: its name between < and >, put where the spaces beside it were, so that nothing shifts, in bold.
fn carried_line(columns: &[ListColumn], values: &[String], sizes: &[usize], style: &str) -> Text {
    let mark = cursor_mark(true);
    let mut line = Text::styled("", style);
    line.append(&format!("{}{}", &mark[..mark.len() - 1], marks::MSG_MOVING_OPEN), Style::PLAIN);
    for (column, ((value, size), place)) in values.iter().zip(sizes).zip(columns).enumerate() {
        let shown = fit_aligned(value, *size, place.align);
        if column > 0 {
            line.append(&format!("{shown} "), Style::PLAIN);
            continue;
        }
        let end = shown.trim_end().chars().count();
        let characters: Vec<char> = shown.chars().collect();
        let carried = if end < *size {
            let before: String = characters[..end].iter().collect();
            let after: String = characters[end + 1..].iter().collect();
            format!("{before}{}{after} ", marks::MSG_MOVING_CLOSE)
        } else {
            format!("{shown}{}", marks::MSG_MOVING_CLOSE)
        };
        line.append(&carried, Style::BOLD);
    }
    line
}

/// The run of places a list with room for so many shows, keeping the cursor's near the middle and the list full at either end.
pub fn shown_around(count: usize, at: usize, room: usize) -> std::ops::Range<usize> {
    let start = (at as i64 - (room / 2) as i64).min(count as i64 - room as i64).max(0) as usize;
    start..(start + room).min(count)
}

impl<L: Listing> Page for ListPage<L> {
    fn follow_renames(&mut self, renames: &crate::history::Renames) {
        self.listing.follow_renames(renames);
    }

    fn still_exists(&self, app: &App) -> bool {
        self.listing.still_exists(app)
    }

    fn caption(&self, app: &App) -> String {
        self.listing
            .caption(app)
            .unwrap_or_else(|| self.listing.crumbs(app).last().map(|crumb| crumb.to_uppercase()).unwrap_or_default())
    }

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
        if self.moving {
            return in_order(class, vec![self.bind(&Keys::DROP), self.bind(&Keys::CARRY)]);
        }
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
        if self.press_named(app, item, key) {
            return;
        }
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
        let mut lines = self.listing.lines_above(app);
        let height = height.saturating_sub(lines.len());
        lines.push(self.row_line(&headings, &sizes, Style::BOLD, false));
        lines.push(Text::default());
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
            let selected = *place == cursor;
            if selected && self.moving {
                lines.push(carried_line(self.listing.columns(), &values, &sizes, style));
            } else {
                lines.push(self.row_line(&values, &sizes, style, selected));
            }
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
