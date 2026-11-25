// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The dialogs (the Python interface/tracker/dialogs/): each asks one thing in a box laid over the page that opened it, and
//! hands its answer back to that page, or runs what it was given to do with it. Today the choice dialog, a list to pick
//! from as you type to search it, and the prompt, a line to type a name or a number on.

use crate::app::App;
use crate::drawing::{cursor_mark, fit, legend, BoxCharacters as Boxes, Style, SPACE};
use crate::forms::nodes::GridCell;
use crate::keybindings::{
    ChoiceDialog as ChoiceKeys, ConfirmDialog as ConfirmKeys, GridChoiceDialog as GridKeys, HelpDialog as HelpKeys, KeyClass, MessageDialog as MessageKeys,
    PromptDialog as PromptKeys, SoundDialog as SoundKeys,
};
use crate::keys::KeyItem;
use crate::page::Page;
use crate::screens::list_page::shown_around;
use crate::text::Text;
use llamatron_strings::{labels, marks, messages, named};

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
    let (held, width) = sized_contents(heading, lines, keys, screen_width);
    box_lines(&held, width)
}

/// What a dialog's box holds, and how wide the box is: as wide as it wants, or as its lines need, within the screen.
fn sized_contents(heading: &dyn Fn(usize) -> Vec<Text>, lines: &dyn Fn(usize) -> Vec<Text>, keys: &[KeyItem], screen_width: usize) -> (Vec<Text>, usize) {
    let widest = screen_width.saturating_sub(DIALOG_MARGIN);
    let mut width = widest.min(DIALOG_WIDTH);
    let mut held = contents(heading, lines, keys, width - DIALOG_MARGIN);
    let needed = held.iter().map(Text::cell_len).max().unwrap_or(0) + DIALOG_MARGIN;
    if needed > width {
        width = widest.min(needed);
        held = contents(heading, lines, keys, width - DIALOG_MARGIN);
    }
    (held, width)
}

/// Lines inside a heavy box of a width.
fn box_lines(held: &[Text], width: usize) -> Vec<Text> {
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
        framed.append_text(line);
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

/// How far down and to the right a flyout's box is drawn from its dialog's, so that the two read as a stack.
pub const FLYOUT_SHIFT: usize = 2;

/// One box drawn over another of the same width, FLYOUT_SHIFT down and to the right, covering what lies under it.
fn stacked(under: &[Text], over: &[Text]) -> Vec<Text> {
    let shift = SPACE.repeat(FLYOUT_SHIFT);
    (0..under.len().max(over.len() + FLYOUT_SHIFT))
        .map(|row| {
            if row < FLYOUT_SHIFT {
                let mut line = under[row].clone();
                line.append(&shift, Style::PLAIN);
                return line;
            }
            let mut line = match under.get(row) {
                Some(below) => below.slice(0, FLYOUT_SHIFT),
                None => Text::plain(&shift),
            };
            line.append_text(&over[row - FLYOUT_SHIFT]);
            line
        })
        .collect()
}

/// The page's lines with a dialog's box laid over them in the middle of the screen, as a modal screen sits over its page; a
/// dialog with a flyout open is placed by its own box alone, shift being how far the flyout reaches past it, so that the
/// dialog stays where it was.
pub fn laid_over(lines: &mut [Text], boxed: &[Text], width: usize, shift: usize) {
    let height = lines.len();
    let box_width = boxed.iter().map(Text::cell_len).max().unwrap_or(0);
    let left = width.saturating_sub(box_width.saturating_sub(shift)) / 2;
    let top = height.saturating_sub(boxed.len().saturating_sub(shift)) / 2;
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

/// How many rows the sound dialog shows at once, the list scrolling to keep the cursor's in view, so that the dialog fits an
/// 80 by 24 console.
const SHOWN_SOUNDS: usize = 12;

/// A sound and the value choosing it answers with.
pub type Sound = (String, usize);

/// A sound chosen from groups, each a row drawn as a button that opens a flyout of its sounds (the Python SoundDialog). Its
/// first rows are choices of their own, such as no sound. / searches every group's sounds at once, and L tries the sound
/// under the cursor. It answers with the value of the sound taken.
pub struct SoundDialog {
    title: String,
    top: Vec<Sound>,
    groups: Vec<(String, Vec<Sound>)>,
    /// The value the dialog opened on.
    current: usize,
    cursor: usize,
    /// The group whose flyout is open, and the cursor's place in it.
    flyout: Option<usize>,
    flyout_place: usize,
    /// What the search has typed, or None while nothing is searched for, and the cursor's place among what it found.
    typed: Option<String>,
    found_place: usize,
    /// Why the sound last tried did not play, shown until the next key.
    said: String,
}

impl SoundDialog {
    /// A sound dialog opened on the row that holds a value: its own row at the top, its group's, or the first.
    pub fn new(title: &str, top: Vec<Sound>, groups: Vec<(String, Vec<Sound>)>, current: usize) -> SoundDialog {
        let cursor = match top.iter().position(|(_, held)| *held == current) {
            Some(place) => place,
            None => groups
                .iter()
                .position(|(_, sounds)| sounds.iter().any(|(_, held)| *held == current))
                .map_or(0, |group| top.len() + group),
        };
        SoundDialog {
            title: title.to_string(),
            top,
            groups,
            current,
            cursor,
            flyout: None,
            flyout_place: 0,
            typed: None,
            found_place: 0,
            said: String::new(),
        }
    }

    /// Every group's sounds that hold what was typed, ignoring case, each as its group, its place there and its label.
    fn found(&self) -> Vec<(usize, usize, String)> {
        let wanted = self.typed.clone().unwrap_or_default().to_lowercase();
        let mut found = Vec::new();
        for (group, (_, sounds)) in self.groups.iter().enumerate() {
            for (place, (label, _)) in sounds.iter().enumerate() {
                if label.to_lowercase().contains(&wanted) {
                    found.push((group, place, label.clone()));
                }
            }
        }
        found
    }

    /// The value of the sound under the cursor, or None on a group's row and while searching.
    fn under_cursor(&self) -> Option<usize> {
        if self.typed.is_some() {
            return None;
        }
        if let Some(group) = self.flyout {
            return self.groups[group].1.get(self.flyout_place).map(|(_, value)| *value);
        }
        self.top.get(self.cursor).map(|(_, value)| *value)
    }

    /// Whether a value is a sound to hear: anything but no sound.
    fn can_try(value: Option<usize>) -> bool {
        value.is_some_and(|value| value != 0)
    }

    /// Why a sound cannot be tried: the song's Preview instrument, where FluidSynth does not play it, must be on a device
    /// of its own that is connected, and llamatron2 lists no devices yet.
    fn trial_refusal(app: &App) -> String {
        use llamatron_model::objects::setlist::Item;
        use llamatron_model::schema::generated::file_format::{InstrumentSetting, Section, SongSetting, FLUIDSYNTH_DEVICE};
        use llamatron_strings::errors;
        let Some(name) = app
            .document
            .song()
            .get_written(SongSetting::PREVIEW_INSTRUMENT)
            .and_then(|value| value.as_str())
            .map(str::to_string)
        else {
            return errors::ERR_NOTHING_TO_TRY_A_SOUND_WITH.to_string();
        };
        let device = match app.document.get_setlist().get_item(Section::INSTRUMENTS, &name) {
            Some(Item::Instrument(instrument)) => instrument
                .get_written(InstrumentSetting::DEVICE)
                .and_then(|value| value.as_str())
                .map(str::to_string),
            _ => None,
        };
        match device {
            None => named(errors::ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE, &[("name", name.as_str().into())]),
            Some(device) if device == FLUIDSYNTH_DEVICE => named(errors::ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED, &[("name", name.as_str().into())]),
            Some(device) => named(
                errors::ERR_PREVIEW_DEVICE_NOT_CONNECTED,
                &[("name", name.as_str().into()), ("device", device.as_str().into())],
            ),
        }
    }

    /// The key that tries the sound under the cursor, where it is one to hear.
    fn trial_keys(&self) -> Vec<KeyItem> {
        if Self::can_try(self.under_cursor()) {
            vec![Self::bind(&SoundKeys::LISTEN)]
        } else {
            Vec::new()
        }
    }

    /// A row's text: a top row's label, or a group drawn as a button, with the current sound after a mark where it holds it.
    fn row_text(&self, row: usize) -> String {
        if let Some((label, _)) = self.top.get(row) {
            return label.clone();
        }
        let (name, sounds) = &self.groups[row - self.top.len()];
        match sounds.iter().find(|(_, held)| *held == self.current) {
            Some((chosen, _)) => named(marks::MSG_FLYOUT_CHOSEN, &[("name", name.as_str().into()), ("chosen", chosen.as_str().into())]),
            None => named(marks::MSG_FLYOUT_CLOSED, &[("name", name.as_str().into())]),
        }
    }

    /// The rows that show, as (place, row), so many of them, scrolled to keep the cursor's in view.
    fn windowed(rows: &[String], at: usize, shown: usize) -> Vec<(usize, String)> {
        let start = (at as i64 - (shown / 2) as i64).min(rows.len() as i64 - shown as i64).max(0) as usize;
        rows.iter().cloned().enumerate().skip(start).take(shown).collect()
    }

    /// A row as drawn: after the cursor's mark, cut to the width, the cursor's in bold.
    fn row_line(text: &str, selected: bool, width: usize) -> Text {
        let line = fit(&format!("{}{text}", cursor_mark(selected)), width);
        if selected {
            Text::styled(&line, Style::BOLD)
        } else {
            Text::plain(&line)
        }
    }

    /// Lines made up to so many rows with blank ones, and under them the line that says why a sound did not play.
    fn padded(&self, mut lines: Vec<Text>, rows: usize) -> Vec<Text> {
        while lines.len() < rows {
            lines.push(Text::default());
        }
        lines.push(Text::styled(&self.said, Style::REFUSAL));
        lines
    }

    /// The dialog's own lines: what the search found, or the rows of the top choices and the groups.
    fn lines(&self, width: usize) -> Vec<Text> {
        if let Some(typed) = &self.typed {
            let found = self.found();
            let at = self.found_place.min(found.len().saturating_sub(1));
            let rows: Vec<String> = found
                .iter()
                .map(|(group, _, label)| {
                    named(
                        marks::MSG_SOUND_FOUND,
                        &[("sound", label.as_str().into()), ("group", self.groups[*group].0.as_str().into())],
                    )
                })
                .collect();
            let mut lines = Vec::new();
            if !typed.is_empty() {
                let shown = named(marks::MSG_SEARCH_SHOWN, &[("text", typed.as_str().into())]);
                lines.push(Text::styled(&fit(&format!("{SPACE}{shown}"), width), Style::DIM));
            }
            let shown: Vec<Text> = Self::windowed(&rows, at, SHOWN_SOUNDS)
                .iter()
                .take(SHOWN_SOUNDS - 1)
                .map(|(place, row)| Self::row_line(row, *place == at, width))
                .collect();
            lines.extend(self.padded(shown, SHOWN_SOUNDS - 1));
            return lines;
        }
        let rows: Vec<String> = (0..self.top.len() + self.groups.len()).map(|row| self.row_text(row)).collect();
        let shown = Self::windowed(&rows, self.cursor, SHOWN_SOUNDS)
            .iter()
            .map(|(place, row)| Self::row_line(row, *place == self.cursor, width))
            .collect();
        self.padded(shown, SHOWN_SOUNDS)
    }

    /// The open flyout's lines, or None: its group as the heading, a sound a row with the cursor's marked, and its keys.
    fn flyout_lines(&self, app: &App, width: usize) -> Option<Vec<Text>> {
        let group = self.flyout.filter(|_| self.typed.is_none())?;
        let (name, sounds) = &self.groups[group];
        let rows: Vec<String> = sounds.iter().map(|(label, _)| label.clone()).collect();
        let shown = Self::windowed(&rows, self.flyout_place, SHOWN_SOUNDS)
            .iter()
            .map(|(place, row)| Self::row_line(row, *place == self.flyout_place, width))
            .collect();
        let mut lines = vec![Text::styled(name, Style::BOLD), Text::default()];
        lines.extend(self.padded(shown, SHOWN_SOUNDS));
        lines.push(Text::default());
        let keys = crate::keys::in_order(self.class(), self.keys(app));
        let shown_keys: Vec<KeyItem> = keys.into_iter().filter(|item| item.shown).collect();
        lines.extend(legend(&shown_keys, width));
        Some(lines)
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&SoundKeys::CLASS, binding)
    }

    /// Choose the sound under the cursor, handing its value back to the page that opened the dialog.
    fn choose(&self, app: &mut App) {
        if let Some(value) = self.under_cursor() {
            app.go_back();
            app.answer(Answer::Chosen(value));
        }
    }
}

impl Page for SoundDialog {
    fn name(&self) -> &'static str {
        "SoundDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &SoundKeys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        if let Some(typed) = &self.typed {
            let mut keys = vec![
                Self::bind(&SoundKeys::CLOSE),
                Self::bind(&SoundKeys::MOVE).wanting_key(),
                Self::bind(&SoundKeys::FIND),
                Self::bind(&SoundKeys::TYPE).wanting_key(),
            ];
            if !typed.is_empty() {
                keys.push(Self::bind(&SoundKeys::ERASE));
                keys.push(Self::bind(&SoundKeys::COMPLETE));
            }
            return keys;
        }
        if self.flyout.is_some() {
            let mut keys = vec![
                Self::bind(&SoundKeys::CLOSE),
                Self::bind(&SoundKeys::MOVE_IN_FLYOUT).wanting_key(),
                Self::bind(&SoundKeys::CHOOSE),
            ];
            keys.extend(self.trial_keys());
            return keys;
        }
        let on_group = self.cursor >= self.top.len();
        let mut keys = vec![Self::bind(&SoundKeys::CANCEL), Self::bind(&SoundKeys::MOVE).wanting_key()];
        keys.push(if on_group {
            Self::bind(&SoundKeys::OPEN)
        } else {
            Self::bind(&SoundKeys::CHOOSE)
        });
        keys.push(Self::bind(&SoundKeys::SEARCH));
        keys.extend(self.trial_keys());
        keys
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        self.said.clear();
        if item.is(&SoundKeys::CANCEL) {
            app.go_back();
        } else if item.is(&SoundKeys::CLOSE) {
            if self.typed.is_some() {
                self.typed = None;
            } else {
                self.flyout = None;
            }
        } else if item.is(&SoundKeys::MOVE) && self.typed.is_some() {
            let found = self.found().len();
            if found > 0 {
                let place = self.found_place.min(found - 1);
                self.found_place = if key == "up" { place.saturating_sub(1) } else { (place + 1).min(found - 1) };
            }
        } else if item.is(&SoundKeys::MOVE) {
            let rows = self.top.len() + self.groups.len();
            self.cursor = if key == "up" {
                self.cursor.saturating_sub(1)
            } else {
                (self.cursor + 1).min(rows.saturating_sub(1))
            };
        } else if item.is(&SoundKeys::MOVE_IN_FLYOUT) {
            let count = self.flyout.map_or(0, |group| self.groups[group].1.len());
            match key {
                "left" => self.flyout = None,
                "up" => self.flyout_place = self.flyout_place.saturating_sub(1),
                "down" => self.flyout_place = (self.flyout_place + 1).min(count.saturating_sub(1)),
                _ => {}
            }
        } else if item.is(&SoundKeys::OPEN) {
            let group = self.cursor - self.top.len();
            self.flyout_place = self.groups[group].1.iter().position(|(_, held)| *held == self.current).unwrap_or(0);
            self.flyout = Some(group);
        } else if item.is(&SoundKeys::CHOOSE) {
            self.choose(app);
        } else if item.is(&SoundKeys::SEARCH) {
            self.typed = Some(String::new());
            self.found_place = 0;
        } else if item.is(&SoundKeys::TYPE) {
            let typed = self.typed.get_or_insert_with(String::new);
            typed.push_str(if key == "space" { SPACE } else { key });
            self.found_place = 0;
        } else if item.is(&SoundKeys::ERASE) {
            if let Some(typed) = self.typed.as_mut() {
                typed.pop();
            }
            self.found_place = 0;
        } else if item.is(&SoundKeys::COMPLETE) {
            let labels: Vec<String> = self.found().into_iter().map(|(_, _, label)| label).collect();
            let typed = self.typed.clone().unwrap_or_default();
            self.typed = Some(completed_from(&labels, &typed));
            self.found_place = 0;
        } else if item.is(&SoundKeys::FIND) {
            let found = self.found();
            if let Some((group, place, _)) = found.get(self.found_place.min(found.len().saturating_sub(1))).cloned() {
                self.typed = None;
                self.cursor = self.top.len() + group;
                self.flyout = Some(group);
                self.flyout_place = place;
            }
        } else if item.is(&SoundKeys::LISTEN) {
            // llamatron2 plays nothing in real time yet, so trying a sound says why it cannot be heard.
            self.said = Self::trial_refusal(app);
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = crate::keys::in_order(self.class(), self.keys(app));
        let shown: Vec<KeyItem> = if self.flyout.is_some() && self.typed.is_none() {
            // The flyout lists the keys; the dialog under it keeps the keys it had while closed.
            let mut closed = vec![Self::bind(&SoundKeys::CANCEL), Self::bind(&SoundKeys::MOVE)];
            closed.push(Self::bind(&SoundKeys::OPEN));
            closed.push(Self::bind(&SoundKeys::SEARCH));
            crate::keys::in_order(self.class(), closed)
        } else {
            keys
        };
        let (held, width_of_box) = sized_contents(&|inner| heading_lines(&self.title, false, inner), &|inner| self.lines(inner), &shown, width);
        let boxed = box_lines(&held, width_of_box);
        let Some(mut over) = self.flyout_lines(app, width_of_box - DIALOG_MARGIN) else {
            return boxed;
        };
        // The flyout's box is as tall as the dialog's, whatever it holds.
        over.resize(held.len(), Text::default());
        stacked(&boxed, &box_lines(&over, width_of_box))
    }

    fn dialog_shift(&self) -> usize {
        if self.flyout.is_some() && self.typed.is_none() {
            FLYOUT_SHIFT
        } else {
            0
        }
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }

    fn takes_text(&self) -> bool {
        self.typed.is_some()
    }

    fn type_text(&mut self, _app: &mut App, character: char) {
        if let Some(typed) = self.typed.as_mut() {
            typed.push(character);
            self.found_place = 0;
        }
    }
}

/// What was typed completed as far as every label found agrees, ignoring case.
fn completed_from(labels: &[String], typed: &str) -> String {
    let lowered = typed.to_lowercase();
    if labels.is_empty() || !labels.iter().all(|label| label.to_lowercase().starts_with(&lowered)) {
        return typed.to_string();
    }
    let first: Vec<char> = labels[0].chars().collect();
    let mut length = typed.chars().count();
    while length < first.len() {
        let longer: String = first[..length + 1].iter().collect::<String>().to_lowercase();
        if !labels.iter().all(|label| label.to_lowercase().starts_with(&longer)) {
            break;
        }
        length += 1;
    }
    first[..length].iter().collect()
}

/// How many columns the help's keys panel lays its keys out in.
const HELP_COLUMNS: usize = 2;

/// The F1 dialog (the Python HelpDialog): every key that works on a page, the everywhere keys above the page's own, laid out
/// in two columns, with Tab, Left and Right turning to what the page is about.
pub struct HelpDialog {
    place: String,
    everywhere: Vec<KeyItem>,
    own: Vec<KeyItem>,
    about: Vec<String>,
    /// The panel showing: the keys first, then what the page is about.
    panel: usize,
}

impl HelpDialog {
    /// The help of a page: where it is, the everywhere keys, its own keys and its help's lines.
    pub fn new(place: &str, everywhere: Vec<KeyItem>, own: Vec<KeyItem>, about: Vec<String>) -> HelpDialog {
        HelpDialog {
            place: place.to_string(),
            everywhere,
            own,
            about,
            panel: 0,
        }
    }

    /// The heading: the page and the panel showing.
    fn title(&self) -> String {
        let panel = labels::MSG_HELP_PANELS[self.panel];
        named(messages::MSG_HELP_TITLE, &[("where", self.place.as_str().into()), ("panel", panel.into())])
    }

    /// The panel's lines: the everywhere keys, a blank line and the page's own keys, or the page's help wrapped to the width.
    fn lines(&self, width: usize) -> Vec<Text> {
        if self.panel == 0 {
            let mut lines = key_columns(&self.everywhere, width, HELP_COLUMNS);
            lines.push(Text::default());
            lines.extend(key_columns(&self.own, width, HELP_COLUMNS));
            return lines;
        }
        self.about.iter().flat_map(|line| crate::drawing::wrapped(line, width)).collect()
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&HelpKeys::CLASS, binding)
    }
}

impl Page for HelpDialog {
    fn name(&self) -> &'static str {
        "HelpDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &HelpKeys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        vec![Self::bind(&HelpKeys::CLOSE), Self::bind(&HelpKeys::OTHER_PANEL)]
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, _key: &str) {
        if item.is(&HelpKeys::CLOSE) {
            app.go_back();
        } else if item.is(&HelpKeys::OTHER_PANEL) {
            self.panel = (self.panel + 1) % labels::MSG_HELP_PANELS.len();
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = crate::keys::in_order(self.class(), self.keys(app));
        let title = self.title();
        dialog_box(&title, false, &|inner| self.lines(inner), &keys, width)
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }
}

/// Keys as lines of so many columns, filled down one column and then the next, each key its label reversed and what it does.
fn key_columns(items: &[KeyItem], width: usize, columns: usize) -> Vec<Text> {
    let rows = items.len().div_ceil(columns);
    let column_width = width / columns;
    (0..rows)
        .map(|row| {
            let mut line = Text::default();
            for column in 0..columns {
                if let Some(item) = items.get(row + column * rows) {
                    line.append_text(&key_cell(item, column_width));
                }
            }
            line
        })
        .collect()
}

/// One key as a cell of a width: its label in reverse video, then what it does, cut and padded to the width.
fn key_cell(item: &KeyItem, width: usize) -> Text {
    let mut cell = Text::default();
    cell.append(&format!("{SPACE}{}{SPACE}", item.label), Style::REVERSE);
    cell.append(&format!("{SPACE}{}", item.what), Style::PLAIN);
    let mut cell = cell.slice(0, width.min(cell.cell_len()));
    let room = width.saturating_sub(cell.cell_len());
    cell.append(&SPACE.repeat(room), Style::PLAIN);
    cell
}

/// What a message or a question shows: each message wrapped to the width, a blank line, and its answers as boxed buttons,
/// each its name alone, the selected one double-lined.
fn message_lines(messages: &[String], buttons: &[&str], selected: usize, width: usize) -> Vec<Text> {
    let mut lines: Vec<Text> = messages.iter().flat_map(|message| crate::drawing::wrapped(message, width)).collect();
    lines.push(Text::default());
    let row: Vec<(String, String)> = buttons.iter().map(|label| (String::new(), label.to_string())).collect();
    lines.extend(crate::forms::drawing::button_row(&row, Some(selected)));
    lines
}

/// A dialog that says one thing and waits for OK (the Python MessageDialog).
pub struct MessageDialog {
    title: String,
    messages: Vec<String>,
}

impl MessageDialog {
    /// A message under a title.
    pub fn new(title: &str, messages: Vec<String>) -> MessageDialog {
        MessageDialog {
            title: title.to_string(),
            messages,
        }
    }
}

impl Page for MessageDialog {
    fn name(&self) -> &'static str {
        "MessageDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &MessageKeys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        vec![KeyItem::of(&MessageKeys::CLASS, &MessageKeys::CLOSE)]
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, _key: &str) {
        if item.is(&MessageKeys::CLOSE) {
            app.go_back();
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = crate::keys::in_order(self.class(), self.keys(app));
        dialog_box(
            &self.title,
            false,
            &|inner| message_lines(&self.messages, &[labels::MSG_OK_BUTTON], 0, inner),
            &keys,
            width,
        )
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }
}

/// The YES button's place among a question's buttons, and NO's.
const YES: usize = 0;
const NO: usize = 1;

/// A YES or NO question (the Python ConfirmDialog): Left and Right move between the buttons, ENTER presses the selected one,
/// and ESC answers NO. YES runs what the dialog was given, or hands YES back to the page that opened it; NO does nothing.
pub struct ConfirmDialog {
    title: String,
    messages: Vec<String>,
    /// A question whose YES gives something up, its title red so that it isn't answered by habit.
    deletes: bool,
    choice: usize,
    then: Option<Then>,
}

impl ConfirmDialog {
    /// A question opening on YES, or on NO where YES is easy to give by accident.
    pub fn new(title: &str, messages: Vec<String>, starts_on_no: bool, deletes: bool) -> ConfirmDialog {
        let choice = if starts_on_no { NO } else { YES };
        ConfirmDialog {
            title: title.to_string(),
            messages,
            deletes,
            choice,
            then: None,
        }
    }

    /// The question running something on YES.
    pub fn then(mut self, then: Then) -> ConfirmDialog {
        self.then = Some(then);
        self
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&ConfirmKeys::CLASS, binding)
    }
}

impl Page for ConfirmDialog {
    fn name(&self) -> &'static str {
        "ConfirmDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &ConfirmKeys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        vec![
            Self::bind(&ConfirmKeys::NO),
            Self::bind(&ConfirmKeys::SELECT).wanting_key(),
            Self::bind(&ConfirmKeys::ANSWER),
        ]
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&ConfirmKeys::NO) {
            app.go_back();
        } else if item.is(&ConfirmKeys::SELECT) {
            self.choice = if key == "left" {
                self.choice.saturating_sub(1)
            } else {
                (self.choice + 1).min(NO)
            };
        } else if item.is(&ConfirmKeys::ANSWER) {
            app.go_back();
            if self.choice != YES {
                return;
            }
            let answer = Answer::Chosen(YES);
            match self.then.as_mut() {
                Some(then) => then(app, &answer),
                None => app.answer(answer),
            }
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = crate::keys::in_order(self.class(), self.keys(app));
        let lines = |inner: usize| message_lines(&self.messages, labels::MSG_CONFIRM_BUTTONS, self.choice, inner);
        dialog_box(&self.title, self.deletes, &lines, &keys, width)
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }
}
