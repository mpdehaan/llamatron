// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The dialogs (the Python interface/tracker/dialogs/): each asks one thing in a box laid over the page that opened it, and
//! hands its answer back to that page, or runs what it was given to do with it. Today the choice dialog, a list to pick
//! from as you type to search it, and the prompt, a line to type a name or a number on.

use crate::app::App;
use crate::drawing::{cursor_mark, fit, legend, BoxCharacters as Boxes, Style, SPACE};
use crate::keybindings::{ChoiceDialog as ChoiceKeys, KeyClass, PromptDialog as PromptKeys};
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
fn contents(title: &str, deletes: bool, lines: &dyn Fn(usize) -> Vec<Text>, keys: &[KeyItem], inner: usize) -> Vec<Text> {
    let mut result = heading_lines(title, deletes, inner);
    result.push(Text::default());
    result.extend(lines(inner));
    result.push(Text::default());
    let shown: Vec<KeyItem> = keys.iter().filter(|item| item.shown).cloned().collect();
    result.extend(legend(&shown, inner));
    result
}

/// A dialog drawn in its heavy box, as wide as it wants or its lines need, within the screen.
pub fn dialog_box(title: &str, deletes: bool, lines: &dyn Fn(usize) -> Vec<Text>, keys: &[KeyItem], screen_width: usize) -> Vec<Text> {
    let widest = screen_width.saturating_sub(DIALOG_MARGIN);
    let mut width = widest.min(DIALOG_WIDTH);
    let mut held = contents(title, deletes, lines, keys, width - DIALOG_MARGIN);
    let needed = held.iter().map(Text::cell_len).max().unwrap_or(0) + DIALOG_MARGIN;
    if needed > width {
        width = widest.min(needed);
        held = contents(title, deletes, lines, keys, width - DIALOG_MARGIN);
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
