// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The check of named values reports exactly the lines of a sample of Rust that type a value in place: the sample,
//! `data/named_values_sample.rs`, marks each such line with the comment `flagged`.

use std::process::Command;

/// The sample, beside the tests; the mark of a line the check must report; and the check, as the build makes it.
const SAMPLE: &str = "tests/data/named_values_sample.rs";
const FLAGGED_MARK: &str = "// flagged";
const CHECK: &str = env!("CARGO_BIN_EXE_check-named-values");
/// How the check writes a report's place: the path, a colon, the line and a colon.
const PLACE_SEPARATOR: char = ':';

/// The check reports the sample's marked lines and no other.
#[test]
fn exactly_the_marked_lines_are_reported() {
    let sample = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(SAMPLE);
    let text = std::fs::read_to_string(&sample).expect("the sample reads");
    let marked: Vec<usize> = text
        .lines()
        .enumerate()
        .filter(|(_, line)| line.contains(FLAGGED_MARK))
        .map(|(place, _)| place + 1)
        .collect();
    let output = Command::new(CHECK).arg(&sample).output().expect("the check runs");
    let reported: Vec<usize> = String::from_utf8_lossy(&output.stdout)
        .lines()
        .filter_map(|line| line.split(PLACE_SEPARATOR).nth(1))
        .filter_map(|number| number.parse().ok())
        .collect();
    assert_eq!(reported, marked);
}
