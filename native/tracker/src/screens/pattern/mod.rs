// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The pages that edit patterns (the Python screens/pattern/).

pub mod pattern_editor;
pub mod patterns_page;
pub mod rows_view;
pub mod whole_pattern;

/// The page that edits a pattern.
pub fn open_pattern(name: &str) -> Box<dyn crate::page::Page> {
    Box::new(pattern_editor::PatternEditor::new(name))
}

/// The page that edits a pattern a clip plays, opened from Arrange or the clip page, whose crumbs come first.
pub fn open_clip_pattern(name: &str, opener_crumbs: Vec<String>, track: &str) -> Box<dyn crate::page::Page> {
    Box::new(pattern_editor::PatternEditor::opened_from(name, opener_crumbs, track))
}
