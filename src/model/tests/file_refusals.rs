// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What a set file refuses as it opens: each small set in `tests/data/refused/` holds one thing the file format does not
//! allow, and opening it fails with the message saying what.

use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::MIN_MORPH_REPEAT;
use llamatron_strings::{errors, named};

/// Each refused set, and the message its refusal holds.
fn refusals() -> Vec<(&'static str, String)> {
    vec![
        (
            "morph_with_one_repeat.yml",
            named(errors::ERR_MORPH_TOO_FEW_REPEATS, &[("lowest", MIN_MORPH_REPEAT.into())]),
        ),
        ("morph_without_its_style.yml", errors::ERR_MORPH_NEEDS_BOTH.to_string()),
    ]
}

/// Every refused set fails to open, saying why.
#[test]
fn each_refused_set_says_why_it_does_not_open() {
    let folder = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data/refused");
    for (file, message) in refusals() {
        let text = std::fs::read_to_string(folder.join(file)).expect("the refused set is there");
        match Setlist::read_text(&text, None) {
            Ok(_) => panic!("{file} opened"),
            Err(problem) => assert!(problem.message.contains(&message), "{file}: {}", problem.message),
        }
    }
}
