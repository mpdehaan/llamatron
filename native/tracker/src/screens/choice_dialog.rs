// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A dialog with a list of choices (the Python dialogs/choice_dialog.py): Up and Down move, ENTER chooses, ESC cancels. Its
//! keys and what a choice does are ported; how it is drawn over the page is not yet, so it names itself not ported, and the
//! screen tour waits on it while it shows.

use crate::app::App;
use crate::keybindings::{ChoiceDialog as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::page::Page;
use crate::text::Text;

/// What a choice does, given its place among the options.
pub type Chosen = Box<dyn FnMut(&mut App, usize)>;

pub struct ChoiceDialog {
    pub title: String,
    pub options: Vec<String>,
    pub current: usize,
    pub then: Chosen,
}

impl Page for ChoiceDialog {
    fn name(&self) -> &'static str {
        crate::screens::not_ported::NOT_PORTED
    }

    fn stack_name(&self) -> &str {
        "ChoiceDialog"
    }

    fn is_ported(&self) -> bool {
        false
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        [&Keys::CANCEL, &Keys::MOVE, &Keys::CHOOSE]
            .into_iter()
            .map(|binding| KeyItem::of(&Keys::CLASS, binding).wanting_key())
            .collect()
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&Keys::CANCEL) {
            app.go_back();
        } else if item.is(&Keys::MOVE) {
            let last = self.options.len().saturating_sub(1);
            self.current = if key == "up" {
                self.current.saturating_sub(1)
            } else {
                (self.current + 1).min(last)
            };
        } else if item.is(&Keys::CHOOSE) {
            app.go_back();
            (self.then)(app, self.current);
        }
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        let mut lines = vec![Text::plain(&self.title)];
        lines.extend(self.options.iter().map(|option| Text::plain(option)));
        lines
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![self.title.clone()]
    }
}
