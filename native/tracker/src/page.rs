// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A page (the Python screens/shared/page.py): a full screen drawn as lines of styled text, the header, the page's body, the
//! status line, a rule and the legend; and what every page answers, its keys, what a key does, and its crumbs and theme.

use crate::app::App;
use crate::drawing::{self, fit, legend, BoxCharacters, Style};
use crate::keybindings::KeyClass;
use crate::keys::{arrows_joined, in_order, KeyItem};
use crate::style::Style as RichStyle;
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_strings::{labels, marks, named};

/// The header's two lines and its rule or stripe.
const HEADER_LINES: usize = 3;
/// A screen at least this tall has a blank line under a theme's stripe.
const ROOM_FOR_THE_GAP: usize = 30;
/// The space between the set's and song's names and the marks at the header's right.
const HEADER_GAP: &str = "  ";
const PROGRAM_NAME: &str = "llamatron";

/// What the header's right shows of time: nothing, or a clock of seconds, None where they aren't known.
pub enum Duration {
    Nothing,
    Seconds(Option<f64>),
    /// A clock worked out exactly, as a pattern's length is.
    Clock(String),
}

pub trait Page {
    /// The Python page's class name, which the screen tour records at each stop.
    fn name(&self) -> &'static str;

    /// The page's name in a stack of pages: its Python class's, which a page not ported yet keeps of the page it stands for.
    fn stack_name(&self) -> &str {
        self.name()
    }

    /// Whether the page stands for one not ported yet.
    fn is_ported(&self) -> bool {
        true
    }

    /// The class of keybindings the page binds from.
    fn class(&self) -> &'static KeyClass;

    /// The page's own keys where its cursor is now.
    fn keys(&self, app: &App) -> Vec<KeyItem>;

    /// Do what a key of the page's own does.
    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str);

    /// The lines between the header and the status line.
    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text>;

    /// The crumbs after the file's.
    fn crumbs(&self, app: &App) -> Vec<String>;

    /// The page's theme colour, or None for the plain rule.
    fn theme(&self) -> Option<Colour> {
        None
    }

    /// What the theme's stripe says the page is doing: its own crumb, in capitals.
    fn caption(&self, app: &App) -> String {
        self.crumbs(app).last().map(|crumb| crumb.to_uppercase()).unwrap_or_default()
    }

    fn duration(&self, _app: &App) -> Duration {
        Duration::Nothing
    }

    /// The page's keys as the F1 dialog lists them.
    fn page_key_table(&self, app: &App) -> Vec<KeyItem> {
        in_order(self.class(), self.keys(app))
    }

    /// The keys the footer shows.
    fn shown_keys(&self, app: &App) -> Vec<KeyItem> {
        self.page_key_table(app).into_iter().filter(|item| item.shown).collect()
    }

    fn shows_legend(&self) -> bool {
        true
    }

    /// What the status line says while nothing else is said.
    fn resting_status(&self, _app: &App) -> String {
        String::new()
    }

    /// Whether typed characters go into text here rather than acting as the page's keys.
    fn takes_text(&self) -> bool {
        false
    }
}

/// Seconds as minutes and seconds, like 3:05, or dashes if they aren't known.
pub fn clock(seconds: Option<f64>) -> String {
    match seconds {
        None => marks::MSG_NO_TIME.to_string(),
        Some(seconds) => {
            let total = seconds.round_ties_even() as i64;
            named(marks::MSG_CLOCK, &[("minutes", (total / 60).into()), ("seconds", (total % 60).into())])
        }
    }
}

/// An exact length of time in seconds as minutes and seconds, rounded half to even as Python rounds a fraction.
pub fn clock_exact(seconds: llamatron_math::Rational) -> String {
    let (numerator, denominator) = (seconds.numerator(), seconds.denominator());
    let floor = numerator.div_euclid(denominator);
    let twice_left = 2 * numerator.rem_euclid(denominator);
    let total = if twice_left > denominator || (twice_left == denominator && floor % 2 != 0) {
        floor + 1
    } else {
        floor
    };
    named(
        marks::MSG_CLOCK,
        &[("minutes", ((total / 60) as i64).into()), ("seconds", ((total % 60) as i64).into())],
    )
}

/// The whole screen of a page at a size: the header, the body, the status line, the rule and the legend.
pub fn page_lines(page: &dyn Page, app: &App, width: usize, height: usize) -> Vec<Text> {
    let top = header(page, app, width, height);
    let bottom = if page.shows_legend() {
        legend(&arrows_joined(page.shown_keys(app)), width)
    } else {
        Vec::new()
    };
    let rule = if bottom.is_empty() {
        Vec::new()
    } else {
        vec![Text::styled(&BoxCharacters::RULE.repeat(width), Style::DIM)]
    };
    let said = app.status.text();
    let resting;
    let shown = if said.is_empty() {
        resting = page.resting_status(app);
        resting.as_str()
    } else {
        said
    };
    let style = if app.status.is_refusal() { Style::REFUSAL } else { Style::DIM };
    let status = Text::styled(&format!(" {}", fit(shown, width.saturating_sub(1))), style);
    let room = height.saturating_sub(top.len() + rule.len() + bottom.len() + 1).max(1);
    let mut lines = page.body(app, width, room);
    lines.truncate(room);
    while lines.len() < room {
        lines.push(Text::default());
    }
    for line in &mut lines {
        line.truncate(width);
    }
    let mut screen = top;
    screen.extend(lines);
    screen.push(status);
    screen.extend(rule);
    screen.extend(bottom);
    screen
}

/// The mark at the header's right: unsaved for a set with no file yet, unsaved changes for one changed since, else saved.
fn save_mark(app: &App) -> &'static str {
    let document = &app.document;
    if document.get_path().is_none() {
        return marks::MSG_UNSAVED_MARK;
    }
    if document.is_dirty() {
        marks::MSG_UNSAVED_CHANGES_MARK
    } else {
        marks::MSG_SAVED_MARK
    }
}

fn time_text(page: &dyn Page, app: &App) -> String {
    match page.duration(app) {
        Duration::Nothing => String::new(),
        Duration::Seconds(seconds) => clock(seconds),
        Duration::Clock(text) => text,
    }
}

/// The header's lines: the crumbs, llamatron centred, the set and the save mark; the song and its length; then the rule or
/// the theme's stripe with the page's caption, and a blank line under the stripe where the screen has room.
pub fn header(page: &dyn Page, app: &App, width: usize, height: usize) -> Vec<Text> {
    let marks = [save_mark(app).to_string(), time_text(page, app)];
    let file = app.document.get_file_name().unwrap_or_else(|| labels::MSG_NO_FILE_CRUMB.to_string());
    let song = app.document.get_current_song_name();
    let song = if song.is_empty() { marks::MSG_NONE_SHOWN } else { song };
    let names = [
        named(labels::MSG_SET_CRUMB, &[("file", file.as_str().into())]),
        named(labels::MSG_SONG_CRUMB, &[("song", song.into())]),
    ];
    let marks_width = marks.iter().map(|mark| mark.chars().count()).max().unwrap_or(0);
    let names_width = names.iter().map(|name| name.chars().count()).max().unwrap_or(0);
    let names_start = (width as i64 - 1 - marks_width as i64 - HEADER_GAP.len() as i64 - names_width as i64).max(1) as usize;
    let crumbs = page.crumbs(app).join(marks::MSG_CRUMB_SEPARATOR);
    let first = header_line(width, &crumbs, &names[0], names_start, &marks[0], Some(PROGRAM_NAME));
    let second = header_line(width, "", &names[1], names_start, &marks[1], None);
    let Some(theme) = page.theme() else {
        return vec![first, second, Text::plain(&BoxCharacters::HEAVY_RULE.repeat(width))];
    };
    let caption = fit(&page.caption(app), width.saturating_sub(2).max(1));
    let caption = caption.trim_end();
    let stripe: String = format!("{:<width$}", format!(" {caption}"), width = width).chars().take(width).collect();
    let (red, green, blue) = themes::caption_colour(theme);
    let style = RichStyle::parse(&format!("bold {} on {}", RichStyle::rgb((red, green, blue)), RichStyle::rgb(theme)));
    let mut lines = vec![first, second, Text::with_style(&stripe, style)];
    if height >= ROOM_FOR_THE_GAP {
        lines.push(Text::default());
    }
    lines
}

/// How many lines the header takes.
pub fn header_lines(page: &dyn Page, height: usize) -> usize {
    HEADER_LINES + usize::from(page.theme().is_some() && height >= ROOM_FOR_THE_GAP)
}

/// One bold header line: the left text in the left corner, the names from names_start, the mark in the right corner, and the
/// centre text exactly in the middle where the rest leave it room.
fn header_line(width: usize, left: &str, names: &str, names_start: usize, mark: &str, centre: Option<&str>) -> Text {
    let mut characters = vec![' '; width];
    let put = |characters: &mut Vec<char>, start: usize, text: &str| {
        for (offset, character) in text.chars().enumerate() {
            if start + offset < characters.len() {
                characters[start + offset] = character;
            }
        }
    };
    let mark_length = mark.chars().count();
    let mark_start = width.saturating_sub(mark_length + 1);
    let mut left_end = names_start as i64 - HEADER_GAP.len() as i64;
    let centre_text = centre.unwrap_or("");
    let centre_length = centre_text.chars().count();
    let centre_start = width.saturating_sub(centre_length) / 2;
    let left_length = left.chars().count();
    if centre.is_some_and(|text| !text.is_empty()) && left_length + 2 <= centre_start && centre_start + centre_length + HEADER_GAP.len() <= names_start {
        put(&mut characters, centre_start, centre_text);
        left_end = left_end.min(centre_start as i64 - 1);
    }
    if !left.is_empty() {
        let shown = fit(left, (left_end - 1).max(1) as usize);
        put(&mut characters, 1, shown.trim_end());
    }
    let room = (mark_start as i64 - HEADER_GAP.len() as i64 - names_start as i64).max(0) as usize;
    let shown_names: String = names.chars().take(room).collect();
    put(&mut characters, names_start, &shown_names);
    put(&mut characters, mark_start, mark);
    let line: String = characters.into_iter().take(width).collect();
    Text::styled(&line, Style::BOLD)
}

pub use drawing::cursor_mark;
