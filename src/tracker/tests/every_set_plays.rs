// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Every set the tests start from, and the comparisons' sets, opens and plays (the sets made to be refused kept apart in
//! `refused/`): each is read, corrected where it holds a
//! value with an allowed one near it, and played into clips without a problem. What lasts of a change to the layout or a
//! new setting is held here, by every set, rather than by a test of the change.

use llamatron_names::words;
use llamatron_tracker::document::Document;
use std::path::{Path, PathBuf};

/// The folders of sets the tests and the comparisons start from, each beside the crate it serves.
const SET_FOLDERS: [&str; 2] = ["tests/data", "../compare/sets"];
/// A set file's extension.
const SET_EXTENSION: &str = words::YML;

/// Every set file in the folders.
fn every_set() -> Vec<PathBuf> {
    let crate_folder = Path::new(env!("CARGO_MANIFEST_DIR"));
    let mut sets = Vec::new();
    for folder in SET_FOLDERS {
        let entries = std::fs::read_dir(crate_folder.join(folder)).unwrap_or_else(|problem| panic!("{folder}: {problem}"));
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|extension| extension.to_str()) == Some(SET_EXTENSION) {
                sets.push(path);
            }
        }
    }
    sets.sort();
    sets
}

/// Every set opens and plays its songs into clips.
#[test]
fn every_set_opens_and_plays() {
    let sets = every_set();
    assert!(!sets.is_empty(), "the sets are found");
    let mut failing = Vec::new();
    for path in sets {
        match Document::open_corrected(&path) {
            Ok(opened) => {
                if let Err(problem) = opened.document.rendered() {
                    failing.push(format!("{} does not play: {problem}", path.display()));
                }
            }
            Err(problem) => failing.push(format!("{} does not open: {problem}", path.display())),
        }
    }
    assert!(failing.is_empty(), "{failing:#?}");
}
