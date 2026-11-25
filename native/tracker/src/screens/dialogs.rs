// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The dialogs (the Python interface/tracker/dialogs/): each asks one thing in a box laid over the page that opened it, and
//! hands its answer back to that page, or runs what it was given to do with it. Today the choice dialog, a list to pick
//! from as you type to search it, and the prompt, a line to type a name or a number on.

use crate::app::App;
use crate::drawing::{cursor_mark, fit, legend, BoxCharacters as Boxes, Style, SPACE};
use crate::forms::nodes::GridCell;
use crate::keybindings::{ChoiceDialog as ChoiceKeys, GridChoiceDialog as GridKeys, KeyClass, PromptDialog as PromptKeys};
use crate::keys::KeyItem;
use crate::page::Page;
use crate::screens::list_page::shown_around;
use crate::text::Text;
use llamatron_strings::{marks, named};

/// How wide a dialog's box is unless what it holds needs more, and the room it keeps from the screen's sides.
const DIALOG_WIDTH: usize = 70;
const DIALOG_MARGIN: usize = 4;
/// How many choices a choice dialog shows at once.
const SHOWN_CHOICES: usize = 12;

/// What a dialog answers: the place of the choice picked, or the text typed.
#[derive(Clone, Debug, PartialEq)]
pub enum Answer {
    Chosen(usize),
    Typed(String),
}

/// What a dialog does with its answer: run something it was given, or hand the answer back to the page that opened it.
pub type Then = Box<dyn FnMut(&mut App, &Answer)>;

/// A dialog's heading, wrapped where it is wider than the box.
fn heading_lines(title: &str, deletes: bool, width: usize) -> Vec<Text> {
    let style = if deletes { Style::DELETE_TITLE } else { Style::BOLD };
    if title.chars().count() <= width {
        return vec![Text::styled(title, style)];
    }
    crate::drawing::wrapped(title, width)
        .iter()
        .map(|line| Text::styled(&line.text(), style))
        .collect()
}

/// What a dialog's box holds at a width: its heading, a blank line, its own lines and, after another blank line, its keys.
fn contents(heading: &dyn Fn(usize) -> Vec<Text>, lines: &dyn Fn(usize) -> Vec<Text>, keys: &[KeyItem], inner: usize) -> Vec<Text> {
    let mut result = heading(inner);
    result.push(Text::default());
    result.extend(lines(inner));
    result.push(Text::default());
    let shown: Vec<KeyItem> = keys.iter().filter(|item| item.shown).cloned().collect();
    result.extend(legend(&shown, inner));
    result
}

/// A dialog drawn in its heavy box, as wide as it wants or its lines need, within the screen.
pub fn dialog_box(title: &str, deletes: bool, lines: &dyn Fn(usize) -> Vec<Text>, keys: &[KeyItem], screen_width: usize) -> Vec<Text> {
    framed_dialog(&|inner| heading_lines(title, deletes, inner), lines, keys, screen_width)
}

/// A dialog drawn in its heavy box with a heading of its own making at the box's inner width.
fn framed_dialog(heading: &dyn Fn(usize) -> Vec<Text>, lines: &dyn Fn(usize) -> Vec<Text>, keys: &[KeyItem], screen_width: usize) -> Vec<Text> {
    let widest = screen_width.saturating_sub(DIALOG_MARGIN);
    let mut width = widest.min(DIALOG_WIDTH);
    let mut held = contents(heading, lines, keys, width - DIALOG_MARGIN);
    let needed = held.iter().map(Text::cell_len).max().unwrap_or(0) + DIALOG_MARGIN;
    if needed > width {
        width = widest.min(needed);
        held = contents(heading, lines, keys, width - DIALOG_MARGIN);
    }
    let inner = width - DIALOG_MARGIN;
    let mut boxed = vec![Text::plain(&format!(
        "{}{}{}",
        Boxes::HEAVY_TOP_LEFT,
        Boxes::HEAVY_RULE.repeat(width - 2),
        Boxes::HEAVY_TOP_RIGHT
    ))];
    for line in held {
        let mut framed = Text::plain(&format!("{}{SPACE}", Boxes::HEAVY_BAR));
        let room = inner.saturating_sub(line.cell_len());
        framed.append_text(&line);
        framed.append(&format!("{}{SPACE}{}", SPACE.repeat(room), Boxes::HEAVY_BAR), Style::PLAIN);
        boxed.push(framed);
    }
    boxed.push(Text::plain(&format!(
        "{}{}{}",
        Boxes::HEAVY_BOTTOM_LEFT,
        Boxes::HEAVY_RULE.repeat(width - 2),
        Boxes::HEAVY_BOTTOM_RIGHT
    )));
    boxed
}

/// The page's lines with a dialog's box laid over them in the middle of the screen, as a modal screen sits over its page.
pub fn laid_over(lines: &mut [Text], boxed: &[Text], width: usize) {
    let height = lines.len();
    let box_width = boxed.iter().map(Text::cell_len).max().unwrap_or(0);
    let left = width.saturating_sub(box_width) / 2;
    let top = height.saturating_sub(boxed.len()) / 2;
    for (place, piece) in boxed.iter().enumerate() {
        let Some(line) = lines.get_mut(top + place) else { break };
        let mut padded = line.clone();
        let short = (left + box_width).saturating_sub(padded.cell_len());
        padded.append(&SPACE.repeat(short), Style::PLAIN);
        let mut laid = padded.slice(0, left);
        laid.append_text(piece);
        laid.append_text(&padded.slice(left + piece.cell_len(), padded.cell_len()));
        *line = laid;
    }
}

/// A list to pick one choice from, which typing searches, a choice under a heading's place passed over.
pub struct ChoiceDialog {
    pub title: String,
    pub options: Vec<String>,
    pub headings: Vec<usize>,
    pub current: usize,
    pub typed: String,
    pub then: Option<Then>,
}

impl ChoiceDialog {
    /// A choice dialog opened on a choice, its answer handed back to the page that opened it.
    pub fn new(title: &str, options: Vec<String>, current: usize) -> ChoiceDialog {
        let current = current.min(options.len().saturating_sub(1));
        ChoiceDialog {
            title: title.to_string(),
            options,
            headings: Vec::new(),
            current,
            typed: String::new(),
            then: None,
        }
    }

    /// The places of the choices the search matches, the headings left out.
    fn matches(&self) -> Vec<usize> {
        let wanted = self.typed.to_lowercase();
        (0..self.options.len())
            .filter(|place| self.options[*place].to_lowercase().contains(&wanted) && !self.headings.contains(place))
            .collect()
    }

    /// The places the list shows: the matches while searching, and every choice with its headings otherwise.
    fn shown_places(&self) -> Vec<usize> {
        if !self.typed.is_empty() || self.headings.is_empty() {
            return self.matches();
        }
        (0..self.options.len()).collect()
    }

    /// Keep the cursor on a match, the first where it is on none.
    fn settle(&mut self) {
        let matches = self.matches();
        if !matches.is_empty() && !matches.contains(&self.current) {
            self.current = matches[0];
        }
    }

    /// The search completed as far as every match agrees.
    fn completed(&self) -> String {
        let names: Vec<&String> = self.matches().iter().map(|place| &self.options[*place]).collect();
        let typed = self.typed.to_lowercase();
        if names.is_empty() || !names.iter().all(|name| name.to_lowercase().starts_with(&typed)) {
            return self.typed.clone();
        }
        let first: Vec<char> = names[0].chars().collect();
        let mut length = self.typed.chars().count();
        while length < first.len() {
            let longer: String = first[..length + 1].iter().collect::<String>().to_lowercase();
            if !names.iter().all(|name| name.to_lowercase().starts_with(&longer)) {
                break;
            }
            length += 1;
        }
        first[..length].iter().collect()
    }

    /// The list's lines: what is typed while searching, then the choices around the cursor.
    fn lines(&self, width: usize) -> Vec<Text> {
        let mut lines = Vec::new();
        if !self.typed.is_empty() {
            let shown = named(marks::MSG_SEARCH_SHOWN, &[("text", self.typed.as_str().into())]);
            lines.push(Text::styled(&fit(&format!("{SPACE}{shown}"), width), Style::DIM));
        }
        let shown = self.shown_places();
        let matches = self.matches();
        let at = if matches.contains(&self.current) {
            shown.iter().position(|place| *place == self.current).unwrap_or(0)
        } else {
            0
        };
        for place in &shown[shown_around(shown.len(), at, SHOWN_CHOICES)] {
            let text = fit(&format!("{}{}", cursor_mark(*place == self.current), self.options[*place]), width);
            let style = if self.headings.contains(place) { Style::DIM } else { Style::PLAIN };
            lines.push(Text::styled(&text, style));
        }
        lines
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&ChoiceKeys::CLASS, binding)
    }
}

impl Page for ChoiceDialog {
    fn name(&self) -> &'static str {
        "ChoiceDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &ChoiceKeys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        let mut keys = vec![
            Self::bind(&ChoiceKeys::CANCEL),
            Self::bind(&ChoiceKeys::MOVE).wanting_key(),
            Self::bind(&ChoiceKeys::CHOOSE),
            Self::bind(&ChoiceKeys::SEARCH).wanting_key(),
        ];
        if !self.typed.is_empty() {
            keys.push(Self::bind(&ChoiceKeys::ERASE));
            keys.push(Self::bind(&ChoiceKeys::COMPLETE));
        }
        keys
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&ChoiceKeys::CANCEL) {
            app.go_back();
        } else if item.is(&ChoiceKeys::MOVE) {
            let matches = self.matches();
            if matches.is_empty() {
                return;
            }
            match matches.iter().position(|place| *place == self.current) {
                None => self.current = matches[0],
                Some(place) => {
                    let moved = if key == "up" {
                        place.saturating_sub(1)
                    } else {
                        (place + 1).min(matches.len() - 1)
                    };
                    self.current = matches[moved];
                }
            }
        } else if item.is(&ChoiceKeys::CHOOSE) {
            if self.matches().contains(&self.current) {
                app.go_back();
                let answer = Answer::Chosen(self.current);
                match self.then.as_mut() {
                    Some(then) => then(app, &answer),
                    None => app.answer(answer),
                }
            }
        } else if item.is(&ChoiceKeys::SEARCH) {
            self.typed.push_str(if key == "space" { SPACE } else { key });
            self.settle();
        } else if item.is(&ChoiceKeys::ERASE) {
            self.typed.pop();
            self.settle();
        } else if item.is(&ChoiceKeys::COMPLETE) {
            self.typed = self.completed();
            self.settle();
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = crate::keys::in_order(self.class(), self.keys(app));
        dialog_box(&self.title, false, &|inner| self.lines(inner), &keys, width)
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }

    fn takes_text(&self) -> bool {
        true
    }

    fn type_text(&mut self, _app: &mut App, character: char) {
        self.typed.push(character);
        self.settle();
    }
}

/// A line to type a name or a number on, the cursor moved by Left and Right.
pub struct PromptDialog {
    pub title: String,
    pub label: String,
    pub value: String,
    pub cursor: usize,
    pub max_length: Option<usize>,
}

impl PromptDialog {
    /// A prompt holding a value to change, the cursor after it.
    pub fn new(title: &str, value: &str) -> PromptDialog {
        PromptDialog {
            title: title.to_string(),
            label: String::new(),
            value: value.to_string(),
            cursor: value.chars().count(),
            max_length: None,
        }
    }

    /// The typed line: the mark, the label and the text around the cursor, the cursor's character reversed.
    fn typed_line(&self, width: usize) -> Text {
        let characters: Vec<char> = self.value.chars().collect();
        let shown = width.saturating_sub(marks::MSG_PROMPT_MARK.chars().count() + self.label.chars().count() + 1);
        let start = (self.cursor + 1).saturating_sub(shown);
        let text: Vec<char> = characters.iter().skip(start).take(shown).copied().collect();
        let at = self.cursor - start;
        let before: String = text[..at.min(text.len())].iter().collect();
        let mut line = Text::plain(&format!("{}{}{before}", marks::MSG_PROMPT_MARK, self.label));
        let under: String = text.get(at).map_or(SPACE.to_string(), |character| character.to_string());
        line.append(&under, Style::REVERSE);
        let after: String = text.iter().skip(at + 1).collect();
        line.append(&after, Style::PLAIN);
        line
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&PromptKeys::CLASS, binding)
    }
}

impl Page for PromptDialog {
    fn name(&self) -> &'static str {
        "PromptDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &PromptKeys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        vec![
            Self::bind(&PromptKeys::CANCEL),
            Self::bind(&PromptKeys::MOVE).wanting_key(),
            Self::bind(&PromptKeys::DONE),
            Self::bind(&PromptKeys::ERASE),
        ]
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        let length = self.value.chars().count();
        if item.is(&PromptKeys::CANCEL) {
            app.go_back();
        } else if item.is(&PromptKeys::MOVE) {
            self.cursor = if key == "left" {
                self.cursor.saturating_sub(1)
            } else {
                (self.cursor + 1).min(length)
            };
        } else if item.is(&PromptKeys::DONE) {
            app.go_back();
            app.answer(Answer::Typed(self.value.clone()));
        } else if item.is(&PromptKeys::ERASE) && self.cursor > 0 {
            let mut characters: Vec<char> = self.value.chars().collect();
            characters.remove(self.cursor - 1);
            self.value = characters.into_iter().collect();
            self.cursor -= 1;
        }
    }

    fn type_text(&mut self, _app: &mut App, character: char) {
        if self.max_length.is_some_and(|most| self.value.chars().count() >= most) {
            return;
        }
        let mut characters: Vec<char> = self.value.chars().collect();
        characters.insert(self.cursor, character);
        self.value = characters.into_iter().collect();
        self.cursor += 1;
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = crate::keys::in_order(self.class(), self.keys(app));
        dialog_box(&self.title, false, &|inner| vec![self.typed_line(inner)], &keys, width)
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }

    fn takes_text(&self) -> bool {
        true
    }
}

/// A page of a grid picker: its name on the top line, or none where the grid is all one page, and its rows of cells.
pub type GridPage = (Option<String>, Vec<Vec<GridCell>>);

/// Choices laid out in a grid, with a line under it saying what the chosen one is (the Python GridChoiceDialog). Up and Down
/// keep to a column; Left and Right go to the next column across, landing on the choice nearest the row the cursor was on.
/// A grid may have pages, named on the top line, which Tab and Shift+Tab turn, and Left and Right off a page's edge; every
/// page is drawn as wide and as tall as the largest, so the box keeps its size.
pub struct GridChoiceDialog {
    title: String,
    options: Vec<String>,
    pages: Vec<GridPage>,
    /// Each page's rows made as wide as its widest, for moving about in.
    page_cells: Vec<Vec<Vec<GridCell>>>,
    page: usize,
    current: usize,
    /// What each choice is, said under the grid, where the picker says so.
    details: Option<Vec<String>>,
}

impl GridChoiceDialog {
    /// A grid picker opened on a choice, on the first page that holds it.
    pub fn new(title: &str, options: Vec<String>, pages: Vec<GridPage>, current: usize, details: Option<Vec<String>>) -> GridChoiceDialog {
        let page_cells: Vec<Vec<Vec<GridCell>>> = pages.iter().map(|(_, grid)| padded_grid(grid)).collect();
        let page = page_cells.iter().position(|cells| find_in(cells, current).is_some()).unwrap_or(0);
        GridChoiceDialog {
            title: title.to_string(),
            options,
            pages,
            page_cells,
            page,
            current,
            details,
        }
    }

    fn cells(&self) -> &Vec<Vec<GridCell>> {
        &self.page_cells[self.page]
    }

    /// How many columns the current page has.
    fn width(&self) -> usize {
        self.cells().first().map_or(0, Vec::len)
    }

    /// The choice at a row and a column of the current page, or None for a heading, a gap or a place off the grid.
    fn option_at(&self, row: usize, column: usize) -> Option<usize> {
        match self.cells().get(row).and_then(|cells| cells.get(column)) {
            Some(GridCell::Choice(place)) => Some(*place),
            _ => None,
        }
    }

    /// The row and column the cursor's choice is at on the current page, the first place where it is not on it.
    fn where_now(&self) -> (usize, usize) {
        find_in(self.cells(), self.current).unwrap_or((0, 0))
    }

    /// The choice in a column nearest to a row, or None where the column has none.
    fn nearest(&self, row: usize, column: usize) -> Option<usize> {
        (0..self.cells().len())
            .filter(|other| self.option_at(*other, column).is_some())
            .min_by_key(|other| (other.abs_diff(row), *other))
            .and_then(|other| self.option_at(other, column))
    }

    /// Go to the next or previous page, landing near a row, starting from a column and moving inward when that column is
    /// empty.
    fn turn(&mut self, step: i64, row: usize, column: usize) {
        let count = self.pages.len() as i64;
        self.page = (self.page as i64 + step).rem_euclid(count) as usize;
        let width = self.width();
        if width == 0 {
            return;
        }
        let column = column.min(width - 1);
        let mut searched = vec![column];
        if column == 0 {
            searched.extend(1..width);
        } else {
            searched.extend((0..column).rev());
        }
        searched.extend(0..width);
        if let Some(found) = searched.into_iter().find_map(|search| self.nearest(row, search)) {
            self.current = found;
        }
    }

    /// Whether a page a step away exists, the first and the last pages stopping Tab and Shift+Tab.
    fn has_page(&self, step: i64) -> bool {
        let turned = self.page as i64 + step;
        turned >= 0 && turned < self.pages.len() as i64
    }

    /// Move the cursor by an arrow: Up and Down within a column or else to the nearest choice of any column, Left and Right
    /// to the next column across that has a choice, or off the page's edge to the next page.
    fn move_cursor(&mut self, key: &str) {
        let (row, column) = self.where_now();
        let width = self.width();
        if key == "up" || key == "down" {
            let rows: Vec<usize> = if key == "up" {
                (0..row).rev().collect()
            } else {
                (row + 1..self.cells().len()).collect()
            };
            let mut columns = vec![column];
            columns.extend(0..width);
            for search in columns {
                if let Some(found) = rows.iter().find_map(|other| self.option_at(*other, search)) {
                    self.current = found;
                    return;
                }
            }
            return;
        }
        let step: i64 = if key == "left" { -1 } else { 1 };
        for offset in 1..=width as i64 {
            let mut target = column as i64 + step * offset;
            if target < 0 || target >= width as i64 {
                if self.pages.len() > 1 {
                    // Off the edge of a page goes to the edge of the next one across, but never from the last page round to
                    // the first.
                    if self.has_page(step) {
                        self.turn(step, row, if step > 0 { 0 } else { width });
                    }
                    return;
                }
                target = target.rem_euclid(width as i64);
            }
            if let Some(found) = self.nearest(row, target as usize) {
                self.current = found;
                return;
            }
        }
    }

    /// Each column's width: as wide as what it holds on any page, and three more.
    fn column_widths(&self) -> Vec<usize> {
        let columns = self.page_cells.iter().map(|cells| cells.first().map_or(0, Vec::len)).max().unwrap_or(0);
        let mut sizes = vec![0; columns];
        for (_, grid) in &self.pages {
            for cells in grid {
                for (column, cell) in cells.iter().enumerate() {
                    let size = match cell {
                        GridCell::Choice(place) => self.options[*place].chars().count(),
                        GridCell::Heading(text) => text.chars().count(),
                        GridCell::Gap => 0,
                    };
                    sizes[column] = sizes[column].max(size);
                }
            }
        }
        sizes.into_iter().map(|size| size + 3).collect()
    }

    /// The top line: the title, and where there are pages, each page's name, the current one reversed, with the keys that
    /// reach the others.
    fn heading(&self, width: usize) -> Vec<Text> {
        if self.pages.len() == 1 {
            return vec![Text::styled(&self.title, Style::BOLD)];
        }
        let mut tabs = Text::default();
        if self.page > 0 {
            tabs.append(marks::MSG_PREVIOUS_PAGE_MARK, Style::BOLD);
        }
        for (number, (name, _)) in self.pages.iter().enumerate() {
            let tab = named(marks::MSG_PAGE_TAB, &[("name", name.as_deref().unwrap_or_default().into())]);
            tabs.append(&tab, if number == self.page { Style::REVERSE } else { Style::DIM });
            if number < self.pages.len() - 1 || self.page < self.pages.len() - 1 {
                tabs.append(SPACE, Style::PLAIN);
            }
        }
        if self.page < self.pages.len() - 1 {
            tabs.append(marks::MSG_NEXT_PAGE_MARK, Style::BOLD);
        }
        // The page names always fit, so the title is cut short rather than widening the dialog.
        let mut line = Text::styled(&fit(&self.title, width.saturating_sub(tabs.cell_len() + 2)), Style::BOLD);
        let room = width.saturating_sub(line.cell_len() + tabs.cell_len());
        line.append(&SPACE.repeat(room), Style::PLAIN);
        line.append_text(&tabs);
        vec![line]
    }

    /// The grid's lines for the current page, made up to the tallest page's height, then what the chosen one is.
    fn lines(&self, width: usize) -> Vec<Text> {
        let sizes = self.column_widths();
        let mut lines: Vec<Text> = self.pages[self.page].1.iter().map(|cells| self.grid_line(cells, &sizes)).collect();
        let tallest = self.pages.iter().map(|(_, grid)| grid.len()).max().unwrap_or(0);
        while lines.len() < tallest {
            lines.push(Text::default());
        }
        if let Some(details) = &self.details {
            lines.push(Text::default());
            lines.push(Text::plain(&fit(details.get(self.current).map_or("", String::as_str), width)));
        }
        lines
    }

    /// One line of the grid: each choice padded like a key label, reversed under the cursor and out to its column's width,
    /// each heading bold in its column, and each gap blank across its column.
    fn grid_line(&self, cells: &[GridCell], sizes: &[usize]) -> Text {
        let mut line = Text::default();
        for (column, cell) in cells.iter().enumerate() {
            let size = sizes[column];
            match cell {
                GridCell::Gap => {
                    line.append(&SPACE.repeat(size), Style::PLAIN);
                }
                GridCell::Heading(text) => {
                    line.append(&fit(&format!("{SPACE}{text}"), size), Style::BOLD);
                }
                GridCell::Choice(place) => {
                    let text = &self.options[*place];
                    let style = if *place == self.current { Style::REVERSE } else { Style::PLAIN };
                    line.append(&format!("{SPACE}{text}{SPACE}"), style);
                    line.append(&SPACE.repeat(size.saturating_sub(text.chars().count() + 2)), Style::PLAIN);
                }
            }
        }
        line
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&GridKeys::CLASS, binding)
    }
}

impl Page for GridChoiceDialog {
    fn name(&self) -> &'static str {
        "GridChoiceDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &GridKeys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        let mut keys = vec![
            Self::bind(&GridKeys::CANCEL),
            Self::bind(&GridKeys::MOVE).wanting_key(),
            Self::bind(&GridKeys::CHOOSE),
        ];
        if self.pages.len() > 1 {
            keys.push(Self::bind(&GridKeys::OTHER_PAGE));
        }
        keys
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&GridKeys::CANCEL) {
            app.go_back();
        } else if item.is(&GridKeys::MOVE) {
            self.move_cursor(key);
        } else if item.is(&GridKeys::CHOOSE) {
            app.go_back();
            app.answer(Answer::Chosen(self.current));
        } else if item.is(&GridKeys::OTHER_PAGE) {
            let step = item.step_of(key).unwrap_or(1);
            if self.has_page(step) {
                let (row, column) = self.where_now();
                self.turn(step, row, column);
            }
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = crate::keys::in_order(self.class(), self.keys(app));
        framed_dialog(&|inner| self.heading(inner), &|inner| self.lines(inner), &keys, width)
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }
}

/// A grid's rows made as wide as its widest, with gaps.
fn padded_grid(grid: &[Vec<GridCell>]) -> Vec<Vec<GridCell>> {
    let width = grid.iter().map(Vec::len).max().unwrap_or(1);
    grid.iter()
        .map(|cells| {
            let mut padded = cells.clone();
            padded.resize(width, GridCell::Gap);
            padded
        })
        .collect()
}

/// Where a choice is among a page's cells, as its row and column, or None.
fn find_in(cells: &[Vec<GridCell>], place: usize) -> Option<(usize, usize)> {
    cells
        .iter()
        .enumerate()
        .find_map(|(row, line)| line.iter().position(|cell| *cell == GridCell::Choice(place)).map(|column| (row, column)))
}

/// A grid's rows from columns of groups, each a heading and its choices' places, with a gap between the groups of a
/// column; a shorter column is blank below its end.
pub fn grouped_grid(columns: &[Vec<(String, Vec<usize>)>]) -> Vec<Vec<GridCell>> {
    let built: Vec<Vec<GridCell>> = columns
        .iter()
        .map(|groups| {
            let mut cells = Vec::new();
            for (heading, items) in groups {
                if !cells.is_empty() {
                    cells.push(GridCell::Gap);
                }
                cells.push(GridCell::Heading(heading.clone()));
                cells.extend(items.iter().map(|place| GridCell::Choice(*place)));
            }
            cells
        })
        .collect();
    let height = built.iter().map(Vec::len).max().unwrap_or(0);
    (0..height)
        .map(|row| built.iter().map(|cells| cells.get(row).cloned().unwrap_or(GridCell::Gap)).collect())
        .collect()
}
