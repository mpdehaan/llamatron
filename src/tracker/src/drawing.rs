// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What every screen draws with (the Python interface/tracker/drawing.py): the styles, the box characters, and the helpers
//! that fit text to a width.

use crate::keys::KeyItem;
use crate::style::Style as RichStyle;
use crate::text::Text;
use llamatron_names::fill;
use llamatron_strings::legends;

pub const ELLIPSIS: char = '…';
pub const SPACE: &str = " ";
pub const INDENT: &str = "  ";
pub const SELECTED_MARK: &str = "▶ ";

/// What a row starts with: the mark when the cursor is on it, and the indent otherwise.
pub fn cursor_mark(selected: bool) -> &'static str {
    if selected {
        SELECTED_MARK
    } else {
        INDENT
    }
}

/// The only styles the tracker draws with, so that it suits any terminal background.
pub struct Style;

impl Style {
    pub const BOLD: &'static str = "bold";
    pub const DIM: &'static str = "dim";
    pub const REVERSE: &'static str = "reverse";
    pub const PLAIN: &'static str = "";
    pub const SELECTED_EDGE: &'static str = "";
    pub const PLAYING: &'static str = "bold red";
    pub const SOUNDING: &'static str = "bold green";
    pub const CHORD_NOTE: &'static str = "green";
    /// A chord's keys and a scale's on a dialog's keyboard, green and cyan by the terminal's palette numbers, as the
    /// Python's dialogs come out of Rich.
    pub const CHORD_KEY: &'static str = "bold color(2)";
    pub const SCALE_KEY: &'static str = "color(6)";
    pub const READ_HEAD: &'static str = "khaki1";
    pub const KEYSWITCH_LIGHT: &'static str = "bold magenta";
    pub const DRAW_LIGHT: &'static str = "bold #be5aff";
    pub const DRAW_LIGHT_REVERSED: &'static str = "bold reverse #be5aff";
    pub const REFUSAL: &'static str = "rgb(255,176,0)";
    /// Red, as the Python's dialogs come out of Rich: by the terminal's palette number, which is its red.
    pub const DELETE_TITLE: &'static str = "bold color(1)";
    pub const DETAILS_DIVIDER: &'static str = "blue";
    /// Arrange's frame of its headings and the line between its main and drum tracks.
    pub const GRID_FRAME: &'static str = "green";
    pub const PLAYING_SCENE: &'static str = "blue";
    pub const DETAILS_LOCKED: &'static str = "green";
    pub const DETAILS_STOCK: &'static str = "red";
    pub const KEY: &'static str = "bold reverse";
}

/// The box-drawing characters the pages draw with.
pub struct BoxCharacters;

impl BoxCharacters {
    pub const HEAVY_RULE: &'static str = "━";
    pub const RULE: &'static str = "─";
    pub const BAR: &'static str = "│";
    pub const DOUBLE_BAR: &'static str = "║";
    pub const DOUBLE_TOP_TEE: &'static str = "╥";
    pub const DOUBLE_BOTTOM_TEE: &'static str = "╨";
    pub const CROSS: &'static str = "┼";
    pub const LEFT_TEE: &'static str = "├";
    pub const RIGHT_TEE: &'static str = "┤";
    pub const DOUBLE_CROSS: &'static str = "╫";
    pub const DOUBLE_TOP_RIGHT_TEE: &'static str = "╖";
    pub const DOUBLE_RIGHT_TEE: &'static str = "╢";
    pub const DOUBLE_BOTTOM_RIGHT_TEE: &'static str = "╜";
    pub const DOUBLE_RULE_DOUBLE_RIGHT_TEE: &'static str = "╣";
    pub const TOP_LEFT: &'static str = "┌";
    pub const TOP_TEE: &'static str = "┬";
    pub const TOP_RIGHT: &'static str = "┐";
    pub const BOTTOM_LEFT: &'static str = "└";
    pub const BOTTOM_TEE: &'static str = "┴";
    pub const BOTTOM_RIGHT: &'static str = "┘";
    pub const HEAVY_TOP_LEFT: &'static str = "┏";
    pub const HEAVY_TOP_RIGHT: &'static str = "┓";
    pub const HEAVY_BOTTOM_LEFT: &'static str = "┗";
    pub const HEAVY_BOTTOM_RIGHT: &'static str = "┛";
    pub const HEAVY_BAR: &'static str = "┃";
    pub const DOUBLE_RULE: &'static str = "═";
    pub const DOUBLE_RULE_LEFT_TEE: &'static str = "╞";
    pub const DOUBLE_RULE_RIGHT_TEE: &'static str = "╡";
    pub const DOUBLE_RULE_CROSS: &'static str = "╪";
    pub const DOUBLE_RULE_DOUBLE_CROSS: &'static str = "╬";
    pub const DOUBLE_RULE_DOUBLE_BOTTOM_TEE: &'static str = "╩";
    pub const DOUBLE_TOP_LEFT: &'static str = "╔";
    pub const DOUBLE_TOP_RIGHT: &'static str = "╗";
    pub const DOUBLE_BOTTOM_LEFT: &'static str = "╚";
    pub const DOUBLE_BOTTOM_RIGHT: &'static str = "╝";
    pub const MORE: &'static str = "›";
}

/// Text with a space on each side, as a key label or a selected value is shown.
pub fn padded(text: &str) -> String {
    format!(" {text} ")
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Align {
    Left,
    Right,
    Center,
}

/// Text cut or padded to exactly a width, cut with an ellipsis, as the Python's fit.
pub fn fit(text: &str, width: usize) -> String {
    fit_aligned(text, width, Align::Left)
}

pub fn fit_aligned(text: &str, width: usize, align: Align) -> String {
    let characters: Vec<char> = text.chars().collect();
    if characters.len() > width {
        if width == 0 {
            return String::new();
        }
        let mut cut: String = characters[..width - 1].iter().collect();
        cut.push(ELLIPSIS);
        return cut;
    }
    let room = width - characters.len();
    match align {
        Align::Right => format!("{}{text}", " ".repeat(room)),
        // Python's str.center puts the odd space on the right, unless the text's length is odd and the room odd too.
        Align::Center => {
            let left = room / 2 + (room & width & 1);
            format!("{}{text}{}", " ".repeat(left), " ".repeat(room - left))
        }
        Align::Left => format!("{text}{}", " ".repeat(room)),
    }
}

/// Text as lines of at most width characters, broken between words, as a dialog shows a message.
pub fn wrapped(text: &str, width: usize) -> Vec<Text> {
    let mut lines = Vec::new();
    let mut line = String::new();
    for word in text.split_whitespace() {
        if !line.is_empty() && line.chars().count() + 1 + word.chars().count() > width {
            lines.push(Text::plain(&line));
            line = word.to_string();
        } else if line.is_empty() {
            line = word.to_string();
        } else {
            line = format!("{line} {word}");
        }
    }
    lines.push(Text::plain(&line));
    lines
}

/// The legend's lines: every key as a reversed label followed by what it does.
pub fn legend(keys: &[KeyItem], width: usize) -> Vec<Text> {
    let mut lines = Vec::new();
    let mut line = Text::plain(SPACE);
    for item in keys {
        let label = llamatron_strings::named(legends::MSG_LEGEND_LABEL, &[(fill::LABEL, item.label.as_str().into())]);
        let what = llamatron_strings::named(legends::MSG_LEGEND_WHAT, &[(fill::WHAT, item.what.as_str().into())]);
        let size = label.chars().count() + what.chars().count();
        if line.cell_len() + size > width && line.cell_len() > 1 {
            lines.push(line);
            line = Text::plain(SPACE);
        }
        line.append(&label, Style::REVERSE);
        line.append(&what, Style::PLAIN);
    }
    lines.push(line);
    lines
}

/// One line of a screen, drawn in pieces that can overlap, for pages that lay a frame over a grid: later writes cover
/// earlier ones.
pub struct Canvas {
    characters: Vec<char>,
    styles: Vec<RichStyle>,
}

impl Canvas {
    pub fn new(width: usize) -> Canvas {
        Canvas {
            characters: vec![' '; width],
            styles: vec![RichStyle::default(); width],
        }
    }

    pub fn write(&mut self, column: i64, text: &str, style: &str) {
        self.write_style(column, text, &RichStyle::parse(style));
    }

    pub fn write_style(&mut self, column: i64, text: &str, style: &RichStyle) {
        for (offset, character) in text.chars().enumerate() {
            let place = column + offset as i64;
            if place >= 0 && (place as usize) < self.characters.len() {
                self.characters[place as usize] = character;
                self.styles[place as usize] = style.clone();
            }
        }
    }

    /// The finished line, one span per run of the same style.
    pub fn text(&self) -> Text {
        let mut result = Text::default();
        let mut start = 0;
        for place in 1..=self.characters.len() {
            if place == self.characters.len() || self.styles[place] != self.styles[start] {
                let piece: String = self.characters[start..place].iter().collect();
                result.append_style(&piece, self.styles[start].clone());
                start = place;
            }
        }
        result
    }
}
