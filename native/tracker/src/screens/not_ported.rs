// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A page the Rust tracker has not ported yet: it shows nothing, and ESC goes back, so that the screen tour goes on to the
//! pages after it, counting its stops apart from real differences.

use crate::app::App;
use crate::keybindings::Page as PageKeys;
use crate::keys::KeyItem;
use crate::page::Page;
use crate::text::Text;

pub struct NotPorted {
    /// The Python page's class name.
    pub name: String,
}

/// The name the screen tour records for a page not ported yet.
pub const NOT_PORTED: &str = "(not ported)";

impl Page for NotPorted {
    fn name(&self) -> &'static str {
        NOT_PORTED
    }

    fn stack_name(&self) -> &str {
        &self.name
    }

    fn is_ported(&self) -> bool {
        false
    }

    fn class(&self) -> &'static crate::keybindings::KeyClass {
        &PageKeys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        vec![KeyItem::of(&PageKeys::CLASS, &PageKeys::BACK)]
    }

    fn press(&mut self, app: &mut App, _item: &KeyItem, _key: &str) {
        app.go_back();
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        vec![Text::plain(&self.name)]
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![self.name.clone()]
    }
}
