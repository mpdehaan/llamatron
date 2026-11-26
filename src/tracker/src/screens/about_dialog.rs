// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The About dialog (the Python dialogs/about_dialog.py), which F3 opens on every page: the cow saying the program's name,
//! the version and when it was built, the links, a quote chosen as it opens, and the licence.

use crate::app::App;
use crate::drawing::wrapped;
use crate::keybindings::{AboutDialog as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::page::Page;
use crate::screens::dialogs::dialog_box;
use crate::text::Text;
use llamatron_math::python_random::PythonRandom;
use llamatron_strings::named;
use llamatron_strings::texts::about;

/// What the speech bubble is drawn with: its top and bottom rules, as wide as the text and the space either side of it.
const BUBBLE_TOP_CHARACTER: &str = "_";
const BUBBLE_BOTTOM_CHARACTER: &str = "-";
const BUBBLE_MARGIN: usize = 2;
/// How often the magic eight ball answers in place of a quote, and how many lines a quote may wrap onto.
const EIGHT_BALL_CHANCE: f64 = 1.0 / 3.0;
const QUOTE_LINES: usize = 4;
/// The name the cow says.
const PROGRAM_NAME: &str = "llamatron";

/// The cow with text in its speech bubble.
fn cow_saying(text: &str) -> Vec<String> {
    let rule_width = text.chars().count() + BUBBLE_MARGIN;
    let mut lines = vec![
        named(about::MSG_COW_BUBBLE_TOP, &[("rule", BUBBLE_TOP_CHARACTER.repeat(rule_width).as_str().into())]),
        named(about::MSG_COW_BUBBLE_TEXT, &[("text", text.into())]),
        named(
            about::MSG_COW_BUBBLE_BOTTOM,
            &[("rule", BUBBLE_BOTTOM_CHARACTER.repeat(rule_width).as_str().into())],
        ),
    ];
    lines.extend(about::MSG_COW.iter().map(|line| line.to_string()));
    lines
}

/// The magic eight ball's answer a third of the time, and otherwise one of the quotes, drawn afresh each time, since it
/// isn't music.
fn random_quote() -> String {
    let mut random = PythonRandom::unseeded();
    if random.random() < EIGHT_BALL_CHANCE {
        let answer = random.choice(about::MSG_EIGHT_BALL_ANSWERS);
        return named(about::MSG_EIGHT_BALL, &[("answer", (*answer).into())]);
    }
    random.choice(about::MSG_ABOUT_QUOTES).to_string()
}

/// The About dialog: what it says, and its quote, chosen as it opens.
pub struct AboutDialog {
    quote: String,
}

impl AboutDialog {
    /// The dialog with a quote chosen now.
    pub fn new() -> AboutDialog {
        AboutDialog { quote: random_quote() }
    }

    /// The dialog's lines at a width: the cow, the version straight under it, the links, the quote set off by blank lines
    /// where it is short, and the licence.
    fn lines(&self, width: usize) -> Vec<Text> {
        let quote: Vec<String> = wrapped(&self.quote, width).iter().take(QUOTE_LINES).map(Text::text).collect();
        // The dialog is exactly 24 lines with a one-line quote, so the blank line below the quote gives way when the quote
        // wraps onto two lines, and the one above when it wraps onto three.
        let mut words = cow_saying(PROGRAM_NAME);
        words.push(about::MSG_ABOUT_POWERED.to_string());
        words.push(named(
            about::MSG_ABOUT_VERSION,
            &[
                ("version", crate::version::PROGRAM_VERSION.into()),
                ("date", crate::version::BUILD_DATE.into()),
                ("time", crate::version::BUILD_TIME.into()),
            ],
        ));
        words.push(about::MSG_ABOUT_WEB.to_string());
        words.push(about::MSG_ABOUT_BLOG.to_string());
        words.push(named(about::MSG_ABOUT_MORE, &[("site", about::MSG_SITE.into())]));
        if quote.len() <= 2 {
            words.push(String::new());
        }
        let short = quote.len() == 1;
        words.extend(quote);
        if short {
            words.push(String::new());
        }
        words.push(about::MSG_ABOUT_LICENSE.to_string());
        let year = crate::version::BUILD_DATE.split('-').next().unwrap_or_default();
        words.push(named(about::MSG_ABOUT_COPYRIGHT, &[("year", year.into())]));
        words.iter().map(|line| Text::plain(line)).collect()
    }
}

impl Default for AboutDialog {
    fn default() -> Self {
        AboutDialog::new()
    }
}

impl Page for AboutDialog {
    fn name(&self) -> &'static str {
        "AboutDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        vec![KeyItem::of(&Keys::CLASS, &Keys::CLOSE)]
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, _key: &str) {
        if item.is(&Keys::CLOSE) {
            app.go_back();
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = self.keys(app);
        dialog_box(about::MSG_ABOUT_TITLE, false, &|inner| self.lines(inner), &keys, width)
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }
}
