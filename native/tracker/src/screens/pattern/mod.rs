// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The pages that edit patterns (the Python screens/pattern/).

pub mod pattern_editor;
pub mod patterns_page;

/// The page that edits a pattern.
pub fn open_pattern(name: &str) -> Box<dyn crate::page::Page> {
    Box::new(pattern_editor::PatternEditor::new(name))
}
