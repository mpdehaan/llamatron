// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The pages that edit patterns (the Python screens/pattern/).

pub mod patterns_page;

/// The page that edits a pattern, which stands not ported until the pattern editor is.
pub fn open_pattern(name: &str) -> Box<dyn crate::page::Page> {
    let _ = name;
    Box::new(crate::screens::not_ported::NotPorted {
        name: "PatternEditor".to_string(),
    })
}
